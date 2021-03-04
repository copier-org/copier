"""Main functions and classes, used to generate or update projects."""

import json
import platform
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict, field, replace
from functools import partial
from itertools import chain
from pathlib import Path
from shutil import rmtree
from typing import Callable, List, Mapping, Optional, Sequence
from unicodedata import normalize

import pathspec
from jinja2.loaders import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from packaging.version import InvalidVersion, Version
from plumbum import ProcessExecutionError, colors
from plumbum.cli.terminal import ask
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from questionary import unsafe_prompt

from .errors import UserMessageError
from .subproject import Subproject
from .template import Template
from .tools import Style, TemporaryDirectory, printf, to_nice_yaml
from .types import (
    AnyByStrDict,
    JSONSerializable,
    OptStr,
    RelativePath,
    StrOrPath,
    StrSeq,
)
from .user_data import DEFAULT_DATA, AnswersMap, Question

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property


__all__ = (
    "run_auto",
    "run_copy",
    "run_update",
    "Worker",
)


@dataclass
class Worker:
    """Copier process state manager.

    This class represents the state of a copier work, and contains methods to
    actually produce the desired work.

    To use it properly, instantiate it by filling properly all dataclass fields.

    Then, execute one of its main methods, which are prefixed with `run_`:

    -   [run_copy][copier.main.Worker.run_copy] to copy a subproject.
    -   [run_update][copier.main.Worker.run_update] to update a subproject.
    -   [run_auto][copier.main.Worker.run_auto] to let it choose whether you
        want to copy or update the subproject.

    Attributes:
        src_path:
            String that can be resolved to a template path, be it local or remote.

            See [copier.vcs.get_repo][].

            If it is `None`, then it means that you are
            [updating a project][updating-a-project], and the original
            `src_path` will be obtained from
            [the answers file][the-copier-answersyml-file].

        dst_path:
            Destination path where to render the subproject.

        answers_file:
            Indicates the path for [the answers file][the-copier-answersyml-file].

            The path must be relative to `dst_path`.

            If it is `None`, the default value will be obtained from
            [copier.template.Template.answers_relpath][].

        vcs_ref:
            Specify the VCS tag/commit to use in the template.

        data:
            Answers to the questionary defined in the template.

        exclude:
            User-chosen additional [file exclusion patterns][exclude].

        use_prereleases:
            Consider prereleases when detecting the *latest* one?

            See [use_prereleases][].

            Useless if specifying a [vcs_ref][].

        skip_if_exists:
            User-chosen additional [file skip patterns][skip_if_exists].

        cleanup_on_error:
            Delete `dst_path` if there's an error?

            See [cleanup_on_error][].

        force:
            When `True`, disable all user interactions.

            See [force][].

        pretend:
            When `True`, produce no real rendering.

            See [pretend][].

        quiet:
            When `True`, disable all output.

            See [quiet][].
    """

    src_path: Optional[str] = None
    dst_path: Path = field(default=".")
    answers_file: Optional[RelativePath] = None
    vcs_ref: OptStr = None
    data: AnyByStrDict = field(default_factory=dict)
    exclude: StrSeq = ()
    use_prereleases: bool = False
    skip_if_exists: StrSeq = ()
    cleanup_on_error: bool = True
    force: bool = False
    pretend: bool = False
    quiet: bool = False

    def _answers_to_remember(self) -> Mapping:
        """Get only answers that will be remembered in the copier answers file."""
        # All internal values must appear first
        answers: AnyByStrDict = {}
        commit = self.template.commit
        src = self.template.url
        for key, value in (("_commit", commit), ("_src_path", src)):
            if value is not None:
                answers[key] = value
        # Other data goes next
        answers.update(
            (k, v)
            for (k, v) in self.answers.combined.items()
            if not k.startswith("_")
            and k not in self.template.secret_questions
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )
        return answers

    def _execute_tasks(self, tasks: Sequence[Mapping]) -> None:
        """Run the given tasks.

        Arguments:
            tasks: The list of tasks to run.
        """
        for i, task in enumerate(tasks):
            task_cmd = task["task"]
            use_shell = isinstance(task_cmd, str)
            if use_shell:
                task_cmd = self._render_string(task_cmd)
            else:
                task_cmd = [self._render_string(str(part)) for part in task_cmd]
            if not self.quiet:
                print(
                    colors.info
                    | f" > Running task {i + 1} of {len(tasks)}: {task_cmd}",
                    file=sys.stderr,
                )
            with local.cwd(self.subproject.local_abspath), local.env(
                **task.get("extra_env", {})
            ):
                subprocess.run(task_cmd, shell=use_shell, check=True, env=local.env)

    def _render_context(self) -> Mapping:
        """Produce render context for Jinja."""
        # Backwards compatibility
        # FIXME Remove it?
        conf = asdict(self)
        conf.update(
            {
                "answers_file": self.answers_relpath,
                "src_path": self.template.local_abspath,
            }
        )
        copied_conf = conf.copy()
        conf["json"] = partial(json.dumps, copied_conf, default=pydantic_encoder)
        return dict(
            DEFAULT_DATA,
            **self.answers.combined,
            _copier_answers=self._answers_to_remember(),
            _copier_conf=conf,
            _folder_name=self.subproject.local_abspath.name,
        )

    def _path_matcher(self, patterns: StrSeq) -> Callable[[Path], bool]:
        """Produce a function that matches against specified patterns."""
        # TODO Is normalization really needed?
        normalized_patterns = (normalize("NFD", pattern) for pattern in patterns)
        spec = pathspec.PathSpec.from_lines("gitwildmatch", normalized_patterns)
        return spec.match_file

    def _solve_render_conflict(self, dst_relpath: Path):
        """Properly solve render conflicts.

        It can ask the user if running in interactive mode.
        """
        assert not dst_relpath.is_absolute()
        printf(
            "conflict",
            dst_relpath,
            style=Style.DANGER,
            quiet=self.quiet,
            file_=sys.stderr,
        )
        if self.match_skip(dst_relpath):
            printf(
                "skip",
                dst_relpath,
                style=Style.OK,
                quiet=self.quiet,
                file_=sys.stderr,
            )
            return False
        if self.force:
            printf(
                "force",
                dst_relpath,
                style=Style.WARNING,
                quiet=self.quiet,
                file_=sys.stderr,
            )
            return True
        return bool(ask(f" Overwrite {dst_relpath}?", default=True))

    def _render_allowed(
        self, dst_relpath: Path, is_dir: bool = False, expected_contents: bytes = b""
    ) -> bool:
        """Determine if a file or directory can be rendered.

        Args:

            dst_relpath:
                Relative path to destination.
            is_dir:
                Indicate if the path must be treated as a directory or not.
            expected_contents:
                Used to compare existing file contents with them. Allows to know if
                rendering is needed.
        """
        assert not dst_relpath.is_absolute()
        assert not expected_contents or not is_dir, "Dirs cannot have expected content"
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if dst_relpath != Path("."):
            if self.match_exclude(dst_relpath):
                return False
        try:
            previous_content = dst_abspath.read_bytes()
        except FileNotFoundError:
            printf(
                "create",
                dst_relpath,
                style=Style.OK,
                quiet=self.quiet,
                file_=sys.stderr,
            )
            return True
        except (IsADirectoryError, PermissionError) as error:
            # HACK https://bugs.python.org/issue43095
            if isinstance(error, PermissionError):
                if not (error.errno == 13 and platform.system() == "Windows"):
                    raise
            if is_dir:
                printf(
                    "identical",
                    dst_relpath,
                    style=Style.IGNORE,
                    quiet=self.quiet,
                    file_=sys.stderr,
                )
                return True
            return self._solve_render_conflict(dst_relpath)
        else:
            if previous_content == expected_contents:
                printf(
                    "identical",
                    dst_relpath,
                    style=Style.IGNORE,
                    quiet=self.quiet,
                    file_=sys.stderr,
                )
                return True
            return self._solve_render_conflict(dst_relpath)

    @cached_property
    def answers(self) -> AnswersMap:
        """Container of all answers to the questionary.

        It asks the user the 1st time it is called, if running interactively.
        """
        result = AnswersMap(
            default=self.template.default_answers,
            init=self.data,
            last=self.subproject.last_answers,
            metadata=self.template.metadata,
        )
        questions: List[Question] = []
        for var_name, details in self.template.questions_data.items():
            if var_name in result.init:
                # Do not ask again
                continue
            questions.append(
                Question(
                    answers=result,
                    ask_user=not self.force,
                    jinja_env=self.jinja_env,
                    var_name=var_name,
                    **details,
                )
            )
        if self.force:
            # Avoid prompting to not requiring a TTy when --force
            for question in questions:
                new_answer = question.get_default()
                previous_answer = result.combined.get(question.var_name)
                if new_answer != previous_answer:
                    result.user[question.var_name] = new_answer
        else:
            # Display TUI and ask user interactively
            result.user.update(
                unsafe_prompt(
                    (question.get_questionary_structure() for question in questions),
                    answers=result.combined,
                )
            )
        return result

    @cached_property
    def answers_relpath(self) -> Path:
        """Obtain the proper relative path for the answers file.

        It comes from:

        1. User choice.
        2. Template default.
        3. Copier default.
        """
        return self.answers_file or self.template.answers_relpath

    @cached_property
    def all_exclusions(self) -> StrSeq:
        """Combine default, template and user-chosen exclusions."""
        return self.template.exclude + tuple(self.exclude)

    @cached_property
    def jinja_env(self) -> SandboxedEnvironment:
        """Return a pre-configured Jinja environment.

        Respects template settings.
        """
        paths = [str(self.template.local_abspath)]
        loader = FileSystemLoader(paths)
        # We want to minimize the risk of hidden malware in the templates
        # so we use the SandboxedEnvironment instead of the regular one.
        # Of course we still have the post-copy tasks to worry about, but at least
        # they are more visible to the final user.
        env = SandboxedEnvironment(loader=loader, **self.template.envops)
        default_filters = {"to_nice_yaml": to_nice_yaml}
        env.filters.update(default_filters)
        return env

    @cached_property
    def match_exclude(self) -> Callable[[Path], bool]:
        """Get a callable to match paths against all exclusions."""
        return self._path_matcher(self.all_exclusions)

    @cached_property
    def match_skip(self) -> Callable[[Path], bool]:
        """Get a callable to match paths against all skip-if-exists patterns."""
        return self._path_matcher(
            map(
                self._render_string,
                tuple(chain(self.skip_if_exists, self.template.skip_if_exists)),
            )
        )

    def _render_file(self, src_abspath: Path) -> None:
        """Render one file.

        Args:

            src_abspath:
                The absolute path to the file that will be rendered.
        """
        # TODO Get from main.render_file()
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template.local_abspath).as_posix()
        src_renderpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self._render_path(src_renderpath)
        if dst_relpath is None:
            return
        if src_abspath.name.endswith(self.template.templates_suffix):
            tpl = self.jinja_env.get_template(str(src_relpath))
            new_content = tpl.render(**self._render_context()).encode()
        else:
            new_content = src_abspath.read_bytes()
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if dst_abspath.is_dir():
            return
        if not self._render_allowed(dst_relpath, expected_contents=new_content):
            return
        if not self.pretend:
            dst_abspath.write_bytes(new_content)

    def _render_folder(self, src_abspath: Path) -> None:
        """Recursively render a folder.

        Args:
            src_path:
                Folder to be rendered. It must be an absolute path within
                the template.
        """
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self._render_path(src_relpath)
        if dst_relpath is None:
            return
        if not self._render_allowed(dst_relpath, is_dir=True):
            return
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if not self.pretend:
            dst_abspath.mkdir(exist_ok=True)
        for file in src_abspath.iterdir():
            if file.is_dir():
                self._render_folder(file)
            else:
                self._render_file(file)

    def _render_path(self, relpath: Path) -> Optional[Path]:
        """Render one relative path.

        Args:
            relpath:
                The relative path to be rendered. Obviously, it can be templated.
        """
        is_template = relpath.name.endswith(self.template.templates_suffix)
        templated_sibling = (
            self.template.local_abspath / f"{relpath}{self.template.templates_suffix}"
        )
        if templated_sibling.exists():
            return None
        rendered_parts = []
        for part in relpath.parts:
            # Skip folder if any part is rendered as an empty string
            part = self._render_string(part)
            if not part:
                return None
            rendered_parts.append(part)
        with suppress(IndexError):
            if is_template:
                rendered_parts[-1] = rendered_parts[-1][
                    : -len(self.template.templates_suffix)
                ]
        result = Path(*rendered_parts)
        if not is_template:
            templated_sibling = (
                self.template.local_abspath
                / f"{result}{self.template.templates_suffix}"
            )
            if templated_sibling.exists():
                return None
        return result

    def _render_string(self, string: str) -> str:
        """Render one templated string.

        Args:
            string:
                The template source string.
        """
        tpl = self.jinja_env.from_string(string)
        return tpl.render(**self._render_context())

    @cached_property
    def subproject(self) -> Subproject:
        """Get related subproject."""
        return Subproject(
            local_abspath=self.dst_path.absolute(),
            answers_relpath=self.answers_file or ".copier-answers.yml",
        )

    @cached_property
    def template(self) -> Template:
        """Get related template."""
        url = self.src_path
        if not url:
            if self.subproject.template is None:
                raise TypeError("Template not found")
            url = self.subproject.template.url
        return Template(url=url, ref=self.vcs_ref, use_prereleases=self.use_prereleases)

    @cached_property
    def template_copy_root(self) -> Path:
        """Absolute path from where to start copying.

        It points to the cloned template local abspath + the rendered subdir, if any.
        """
        subdir = self._render_string(self.template.subdirectory) or ""
        return self.template.local_abspath / subdir

    # Main operations
    def run_auto(self) -> None:
        """Copy or update automatically.

        If `src_path` was supplied, execute
        [run_copy][copier.main.Worker.run_copy].

        Otherwise, execute [run_update][copier.main.Worker.run_update].
        """
        if self.src_path:
            return self.run_copy()
        return self.run_update()

    def run_copy(self) -> None:
        """Generate a subproject from zero, ignoring what was in the folder.

        If `dst_path` was missing, it will be
        created. Otherwise, `src_path` be rendered
        directly into it, without worrying about evolving what was there
        already.

        See [generating a project][generating-a-project].
        """
        was_existing = self.subproject.local_abspath.exists()
        if not self.quiet:
            # TODO Unify printing tools
            print("")  # padding space
        src_abspath = self.template_copy_root
        try:
            self._render_folder(src_abspath)
            if not self.quiet:
                # TODO Unify printing tools
                print("")  # padding space
            self._execute_tasks(
                [
                    {"task": t, "extra_env": {"STAGE": "task"}}
                    for t in self.template.tasks
                ],
            )
        except Exception:
            if not was_existing and self.cleanup_on_error:
                rmtree(self.subproject.local_abspath)
            raise
        if not self.quiet:
            # TODO Unify printing tools
            print("")  # padding space

    def run_update(self) -> None:
        """Update a subproject that was already generated.

        See [updating a project][updating-a-project].
        """
        # Check all you need is there
        if self.subproject.vcs != "git":
            raise UserMessageError(
                "Updating is only supported in git-tracked subprojects."
            )
        if self.subproject.is_dirty():
            raise UserMessageError(
                "Destination repository is dirty; cannot continue. "
                "Please commit or stash your local changes and retry."
            )
        if self.subproject.template is None or self.subproject.template.ref is None:
            raise UserMessageError(
                "Cannot update because cannot obtain old template references "
                f"from `{self.subproject.answers_relpath}`."
            )
        if self.template.commit is None:
            raise UserMessageError(
                "Updating is only supported in git-tracked templates."
            )
        downgrading = False
        try:
            downgrading = Version(self.subproject.template.ref) > Version(
                self.template.commit
            )
        except InvalidVersion:
            print(
                colors.warn
                | f"Either {self.subproject.template.ref} or {self.template.commit} is not a PEP 440 valid version.",
                file=sys.stderr,
            )
        if downgrading:
            raise UserMessageError(
                f"Your are downgrading from {self.subproject.template.ref} to {self.template.commit}. "
                "Downgrades are not supported."
            )
        # Copy old template into a temporary destination
        with TemporaryDirectory(prefix=f"{__name__}.update_diff.") as dst_temp:
            old_worker = replace(
                self,
                dst_path=dst_temp,
                data=self.subproject.last_answers,
                force=True,
                quiet=True,
                src_path=self.subproject.template.url,
                vcs_ref=self.subproject.template.commit,
            )
            old_worker.run_copy()
            # Extract diff between temporary destination and real destination
            with local.cwd(dst_temp):
                git("init", retcode=None)
                git("add", ".")
                git("config", "user.name", "Copier")
                git("config", "user.email", "copier@copier")
                # 1st commit could fail if any pre-commit hook reformats code
                git("commit", "--allow-empty", "-am", "dumb commit 1", retcode=None)
                git("commit", "--allow-empty", "-am", "dumb commit 2")
                git("config", "--unset", "user.name")
                git("config", "--unset", "user.email")
                git(
                    "remote",
                    "add",
                    "real_dst",
                    self.subproject.local_abspath.absolute(),
                )
                git("fetch", "--depth=1", "real_dst", "HEAD")
                diff_cmd = git["diff-tree", "--unified=1", "HEAD...FETCH_HEAD"]
                try:
                    diff = diff_cmd("--inter-hunk-context=-1")
                except ProcessExecutionError:
                    print(
                        colors.warn
                        | "Make sure Git >= 2.24 is installed to improve updates.",
                        file=sys.stderr,
                    )
                    diff = diff_cmd("--inter-hunk-context=0")
        # Run pre-migration tasks
        self._execute_tasks(
            self.template.migration_tasks(
                "before", self.subproject.template.ref, self.template.commit
            )
        )
        # Clear last answers cache to load possible answers migration
        with suppress(AttributeError):
            del self.answers
        with suppress(AttributeError):
            del self.subproject.last_answers
        # Do a normal update in final destination
        self.run_copy()
        # Try to apply cached diff into final destination
        with local.cwd(self.subproject.local_abspath):
            apply_cmd = git["apply", "--reject", "--exclude", self.answers_relpath]
            for skip_pattern in self.skip_if_exists:
                apply_cmd = apply_cmd["--exclude", skip_pattern]
            (apply_cmd << diff)(retcode=None)
        # Run post-migration tasks
        self._execute_tasks(
            self.template.migration_tasks(
                "after", self.subproject.template.ref, self.template.commit
            )
        )


def run_copy(
    src_path: str,
    dst_path: StrOrPath = ".",
    data: AnyByStrDict = None,
    **kwargs,
) -> Worker:
    """Copy a template to a destination, from zero.

    This is a shortcut for [run_copy][copier.main.Worker.run_copy].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if data is not None:
        kwargs["data"] = data
    worker = Worker(src_path=src_path, dst_path=dst_path, **kwargs)
    worker.run_copy()
    return worker


def run_update(
    dst_path: StrOrPath = ".",
    data: AnyByStrDict = None,
    **kwargs,
) -> Worker:
    """Update a subproject, from its template.

    This is a shortcut for [run_update][copier.main.Worker.run_update].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if data is not None:
        kwargs["data"] = data
    worker = Worker(dst_path=dst_path, **kwargs)
    worker.run_update()
    return worker


def run_auto(
    src_path: OptStr = None,
    dst_path: StrOrPath = ".",
    data: AnyByStrDict = None,
    **kwargs,
) -> Worker:
    """Generate or update a subproject.

    This is a shortcut for [run_auto][copier.main.Worker.run_auto].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if src_path is None:
        return run_update(dst_path, data, **kwargs)
    return run_copy(src_path, dst_path, data, **kwargs)
