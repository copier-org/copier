"""Main functions and classes, used to generate or update projects."""

import os
import platform
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict, field, replace
from filecmp import dircmp
from functools import partial
from itertools import chain
from pathlib import Path
from shutil import rmtree
from typing import Callable, Iterable, Mapping, Optional, Sequence, Union
from unicodedata import normalize

from jinja2.loaders import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from pathspec import PathSpec
from plumbum import ProcessExecutionError, colors
from plumbum.cli.terminal import ask
from plumbum.cmd import git
from plumbum.machines import local
from pydantic import ConfigDict, Extra, PositiveInt
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from questionary import unsafe_prompt

from .errors import CopierAnswersInterrupt, ExtensionNotFoundError, UserMessageError
from .subproject import Subproject
from .template import Task, Template
from .tools import Style, TemporaryDirectory, printf, readlink
from .types import (
    MISSING,
    AnyByStrDict,
    JSONSerializable,
    Literal,
    OptStr,
    RelativePath,
    StrOrPath,
    StrSeq,
)
from .user_data import DEFAULT_DATA, AnswersMap, Question

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property

# Backport of `shutil.copytree` for python 3.7 to accept `dirs_exist_ok` argument
if sys.version_info >= (3, 8):
    from shutil import copytree
else:
    from distutils.dir_util import copy_tree

    def copytree(src: Path, dst: Path, dirs_exist_ok: bool = False):
        """Backport of `shutil.copytree` with `dirs_exist_ok` argument.

        Can be remove once python 3.7 dropped.
        """
        copy_tree(str(src), str(dst))


@dataclass(config=ConfigDict(extra=Extra.forbid))
class Worker:
    """Copier process state manager.

    This class represents the state of a copier work, and contains methods to
    actually produce the desired work.

    To use it properly, use it as a context manager and fill all dataclass fields.

    Then, execute one of its main methods, which are prefixed with `run_`:

    -   [run_copy][copier.main.Worker.run_copy] to copy a subproject.
    -   [run_update][copier.main.Worker.run_update] to update a subproject.
    -   [run_auto][copier.main.Worker.run_auto] to let it choose whether you
        want to copy or update the subproject.

    Example:
        ```python
        with Worker(
            src_path="https://github.com/copier-org/autopretty.git", "output"
        ) as worker:
            worker.run_copy()
        ```

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

        defaults:
            When `True`, use default answers to questions, which might be null if not specified.

            See [defaults][].

        user_defaults:
            Specify user defaults that may override a template's defaults during question prompts.

        overwrite:
            When `True`, Overwrite files that already exist, without asking.

            See [overwrite][].

        pretend:
            When `True`, produce no real rendering.

            See [pretend][].

        quiet:
            When `True`, disable all output.

            See [quiet][].

        conflict:
            One of "rej" (default), "inline" (still experimental).

        context_lines:
            Lines of context to consider when solving conflicts in updates.

            With more lines, context resolution is more accurate, but it will
            also produce more conflicts if your subproject has evolved.

            With less lines, context resolution is less accurate, but it will
            respect better the evolution of your subproject.
    """

    src_path: Optional[str] = None
    dst_path: Path = field(default=Path("."))
    answers_file: Optional[RelativePath] = None
    vcs_ref: OptStr = None
    data: AnyByStrDict = field(default_factory=dict)
    exclude: StrSeq = ()
    use_prereleases: bool = False
    skip_if_exists: StrSeq = ()
    cleanup_on_error: bool = True
    defaults: bool = False
    user_defaults: AnyByStrDict = field(default_factory=dict)
    overwrite: bool = False
    pretend: bool = False
    quiet: bool = False
    conflict: str = "rej"
    context_lines: PositiveInt = 1

    def __enter__(self):
        """Allow using worker as a context manager."""
        return self

    def __exit__(self, type, value, traceback):
        """Clean up garbage files after worker usage ends."""
        if value is not None:
            # exception was raised from code inside context manager:
            # try to clean up, ignoring any exception, then re-raise
            with suppress(Exception):
                self._cleanup()
            raise value
        # otherwise clean up and let any exception bubble up
        self._cleanup()

    def _cleanup(self):
        self.template._cleanup()

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
            (str(k), v)
            for (k, v) in self.answers.combined.items()
            if not k.startswith("_")
            and k not in self.template.secret_questions
            and k in self.template.questions_data
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )
        return answers

    def _execute_tasks(self, tasks: Sequence[Task]) -> None:
        """Run the given tasks.

        Arguments:
            tasks: The list of tasks to run.
        """
        for i, task in enumerate(tasks):
            task_cmd = task.cmd
            if isinstance(task_cmd, str):
                task_cmd = self._render_string(task_cmd)
                use_shell = True
            else:
                task_cmd = [self._render_string(str(part)) for part in task_cmd]
                use_shell = False
            if not self.quiet:
                print(
                    colors.info
                    | f" > Running task {i + 1} of {len(tasks)}: {task_cmd}",
                    file=sys.stderr,
                )
            if self.pretend:
                continue
            with local.cwd(self.subproject.local_abspath), local.env(**task.extra_env):
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
                "vcs_ref_hash": self.template.commit_hash,
                "sep": os.sep,
            }
        )

        return dict(
            DEFAULT_DATA,
            **self.answers.combined,
            _copier_answers=self._answers_to_remember(),
            _copier_conf=conf,
            _folder_name=self.subproject.local_abspath.name,
            _copier_python=sys.executable,
        )

    def _path_matcher(self, patterns: Iterable[str]) -> Callable[[Path], bool]:
        """Produce a function that matches against specified patterns."""
        # TODO Is normalization really needed?
        normalized_patterns = (normalize("NFD", pattern) for pattern in patterns)
        spec = PathSpec.from_lines("gitwildmatch", normalized_patterns)
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
        if self.overwrite or dst_relpath == self.answers_relpath:
            printf(
                "overwrite",
                dst_relpath,
                style=Style.WARNING,
                quiet=self.quiet,
                file_=sys.stderr,
            )
            return True
        return bool(ask(f" Overwrite {dst_relpath}?", default=True))

    def _render_allowed(
        self,
        dst_relpath: Path,
        is_dir: bool = False,
        is_symlink: bool = False,
        expected_contents: Union[bytes, Path] = b"",
    ) -> bool:
        """Determine if a file or directory can be rendered.

        Args:
            dst_relpath:
                Relative path to destination.
            is_dir:
                Indicate if the path must be treated as a directory or not.
            is_symlink:
                Indicate if the path must be treated as a symlink or not.
            expected_contents:
                Used to compare existing file contents with them. Allows to know if
                rendering is needed.
        """
        assert not dst_relpath.is_absolute()
        assert not expected_contents or not is_dir, "Dirs cannot have expected content"
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if dst_relpath != Path(".") and self.match_exclude(dst_relpath):
            return False
        try:
            previous_content: Union[bytes, Path]
            if is_symlink:
                previous_content = readlink(dst_abspath)
            else:
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
        except PermissionError as error:
            # HACK https://bugs.python.org/issue43095
            if not (error.errno == 13 and platform.system() == "Windows"):
                raise
        except IsADirectoryError:
            assert is_dir
        if is_dir or previous_content == expected_contents:
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
            user_defaults=self.user_defaults,
            init=self.data,
            last=self.subproject.last_answers,
            metadata=self.template.metadata,
        )

        for var_name, details in self.template.questions_data.items():
            question = Question(
                answers=result,
                jinja_env=self.jinja_env,
                var_name=var_name,
                **details,
            )
            if var_name in result.init:
                # Try to parse the answer value.
                answer = question.parse_answer(result.init[var_name])
                # Try to validate the answer value if the question has a
                # validator.
                question.validate_answer(answer)
                # At this point, the answer value is valid. Do not ask the
                # question again, but set answer as the user's answer instead.
                result.user[var_name] = answer
                continue

            # Display TUI and ask user interactively only without --defaults
            try:
                if self.defaults:
                    new_answer = question.get_default()
                    if new_answer is MISSING:
                        raise ValueError(f'Question "{var_name}" is required')
                else:
                    new_answer = unsafe_prompt(
                        [question.get_questionary_structure()], answers=result.combined
                    )[question.var_name]
            except KeyboardInterrupt as err:
                raise CopierAnswersInterrupt(result, question, self.template) from err
            previous_answer = result.combined.get(question.var_name)
            # If question was skipped and it's the 1st
            # run, you could be getting a raw templated value
            default_answer = result.default.get(question.var_name)
            if new_answer == default_answer:
                new_answer = question.render_value(default_answer)
                new_answer = question.filter_answer(new_answer)
            if new_answer != previous_answer:
                result.user[question.var_name] = new_answer

        return result

    @cached_property
    def answers_relpath(self) -> Path:
        """Obtain the proper relative path for the answers file.

        It comes from:

        1. User choice.
        2. Template default.
        3. Copier default.
        """
        path = self.answers_file or self.template.answers_relpath
        template = self.jinja_env.from_string(str(path))
        return Path(template.render(**self.answers.combined))

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
        default_extensions = [
            "jinja2_ansible_filters.AnsibleCoreFiltersExtension",
        ]
        extensions = default_extensions + list(self.template.jinja_extensions)
        # We want to minimize the risk of hidden malware in the templates
        # so we use the SandboxedEnvironment instead of the regular one.
        # Of course we still have the post-copy tasks to worry about, but at least
        # they are more visible to the final user.
        try:
            env = SandboxedEnvironment(
                loader=loader, extensions=extensions, **self.template.envops
            )
        except ModuleNotFoundError as error:
            raise ExtensionNotFoundError(
                f"Copier could not load some Jinja extensions:\n{error}\n"
                "Make sure to install these extensions alongside Copier itself.\n"
                "See the docs at https://copier.readthedocs.io/en/latest/configuring/#jinja_extensions"
            )
        # patch the `to_json` filter to support Pydantic dataclasses
        env.filters["to_json"] = partial(
            env.filters["to_json"], default=pydantic_encoder
        )

        # Add a global function to join filesystem paths.
        separators = {
            "posix": "/",
            "windows": "\\",
            "native": os.path.sep,
        }

        def _pathjoin(
            *path: str, mode: Literal["posix", "windows", "native"] = "posix"
        ) -> str:
            return separators[mode].join(path)

        env.globals["pathjoin"] = _pathjoin
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
            try:
                tpl = self.jinja_env.get_template(src_relpath)
            except UnicodeDecodeError:
                if self.template.templates_suffix:
                    # suffix is not empty, re-raise
                    raise
                # suffix is empty, fallback to copy
                new_content = src_abspath.read_bytes()
            else:
                new_content = tpl.render(**self._render_context()).encode()
        else:
            new_content = src_abspath.read_bytes()
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        src_mode = src_abspath.stat().st_mode
        if not self._render_allowed(dst_relpath, expected_contents=new_content):
            return
        if not self.pretend:
            dst_abspath.parent.mkdir(parents=True, exist_ok=True)
            dst_abspath.write_bytes(new_content)
            dst_abspath.chmod(src_mode)

    def _render_symlink(self, src_abspath: Path) -> None:
        """Render one symlink.

        Args:
            src_abspath:
                Symlink to be rendered. It must be an absolute path within
                the template.
        """
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self._render_path(src_relpath)
        if dst_relpath is None:
            return
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)

        src_target = readlink(src_abspath)
        if src_abspath.name.endswith(self.template.templates_suffix):
            dst_target = Path(self._render_string(str(src_target)))
        else:
            dst_target = src_target

        if not self._render_allowed(
            dst_relpath,
            expected_contents=dst_target,
            is_symlink=True,
        ):
            return

        if not self.pretend:
            # symlink_to doesn't overwrite existing files, so delete it first
            if dst_abspath.is_symlink() or dst_abspath.exists():
                dst_abspath.unlink()
            dst_abspath.symlink_to(dst_target)
            if sys.platform == "darwin":
                # Only macOS supports permissions on symlinks.
                # Other platforms just copy the permission of the target
                src_mode = src_abspath.lstat().st_mode
                dst_abspath.lchmod(src_mode)

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
            dst_abspath.mkdir(parents=True, exist_ok=True)
        for file in src_abspath.iterdir():
            if file.is_dir():
                self._render_folder(file)
            elif file.is_symlink() and self.template.preserve_symlinks:
                self._render_symlink(file)
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
        # With an empty suffix, the templated sibling always exists.
        if templated_sibling.exists() and self.template.templates_suffix:
            return None
        if self.template.templates_suffix and is_template:
            relpath = relpath.with_suffix("")
        rendered_parts = []
        for part in relpath.parts:
            # Skip folder if any part is rendered as an empty string
            part = self._render_string(part)
            if not part:
                return None
            # {{ _copier_conf.answers_file }} becomes the full path; in that case,
            # restore part to be just the end leaf
            if str(self.answers_relpath) == part:
                part = Path(part).name
            rendered_parts.append(part)
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
            answers_relpath=self.answers_file or Path(".copier-answers.yml"),
        )

    @cached_property
    def template(self) -> Template:
        """Get related template."""
        url = self.src_path
        if not url:
            if self.subproject.template is None:
                raise TypeError("Template not found")
            url = str(self.subproject.template.url)
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
        src_abspath = self.template_copy_root
        try:
            if not self.quiet:
                # TODO Unify printing tools
                print(
                    f"\nCopying from template version {self.template.version}",
                    file=sys.stderr,
                )
            self._render_folder(src_abspath)
            if not self.quiet:
                # TODO Unify printing tools
                print("")  # padding space
            self._execute_tasks(self.template.tasks)
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
        if not self.subproject.template.version:
            raise UserMessageError(
                "Cannot update: version from last update not detected."
            )
        if not self.template.version:
            raise UserMessageError("Cannot update: version from template not detected.")
        if self.subproject.template.version > self.template.version:
            raise UserMessageError(
                f"Your are downgrading from {self.subproject.template.version} to {self.template.version}. "
                "Downgrades are not supported."
            )
        if not self.quiet:
            # TODO Unify printing tools
            print(
                f"Updating to template version {self.template.version}", file=sys.stderr
            )
        self._apply_update()

    def _apply_update(self):
        subproject_top = Path(
            git(
                "-C",
                self.subproject.local_abspath,
                "rev-parse",
                "--show-toplevel",
            ).strip()
        )
        subproject_subdir = self.subproject.local_abspath.relative_to(subproject_top)

        with TemporaryDirectory(
            prefix=f"{__name__}.old_copy."
        ) as old_copy, TemporaryDirectory(prefix=f"{__name__}.new_copy.") as new_copy:
            # Copy old template into a temporary destination
            old_worker = replace(
                self,
                dst_path=old_copy / subproject_subdir,
                data=self.subproject.last_answers,
                defaults=True,
                quiet=True,
                src_path=self.subproject.template.url,
                vcs_ref=self.subproject.template.commit,
            )
            old_worker.run_copy()
            # Extract diff between temporary destination and real destination
            with local.cwd(old_copy):
                self._git_initialize_repo()
                git("remote", "add", "real_dst", "file://" + str(subproject_top))
                git("fetch", "--depth=1", "real_dst", "HEAD")
                diff_cmd = git[
                    "diff-tree", f"--unified={self.context_lines}", "HEAD...FETCH_HEAD"
                ]
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
                self.template.migration_tasks("before", self.subproject.template)
            )
            # Clear last answers cache to load possible answers migration
            with suppress(AttributeError):
                del self.answers
            with suppress(AttributeError):
                del self.subproject.last_answers
            # Do a normal update in final destination
            self.run_copy()
            # Render with the same answers in an empty dir to avoid pollution
            new_worker = replace(
                self,
                dst_path=new_copy / subproject_subdir,
                data=self.answers.combined,
                defaults=True,
                quiet=True,
                src_path=self.subproject.template.url,
            )
            new_worker.run_copy()
            compared = dircmp(old_copy, new_copy)
            # Try to apply cached diff into final destination
            with local.cwd(subproject_top):
                apply_cmd = git["apply", "--reject", "--exclude", self.answers_relpath]
                for skip_pattern in chain(
                    self.skip_if_exists, self.template.skip_if_exists
                ):
                    apply_cmd = apply_cmd["--exclude", skip_pattern]
                (apply_cmd << diff)(retcode=None)
                # TODO Test more, remove from experimental, make default
                if self.conflict == "inline":
                    status = git("status", "--porcelain").strip().splitlines()
                    for line in status:
                        # Find merge rejections
                        if not (line.startswith("?? ") and line.endswith(".rej")):
                            continue
                        # FIXME Test with a file named '`â ñ"', see it fail, fix it
                        fname = line[3:-4]
                        # Undo possible non-rejected chunks
                        git("checkout", "--", fname)
                        # 3-way-merge the file directly
                        git(
                            "merge-file",
                            "-L",
                            "before updating",
                            "-L",
                            "last update",
                            "-L",
                            "after updating",
                            fname,
                            Path(old_copy) / fname,
                            Path(new_copy) / fname,
                            retcode=None,
                        )
                        # Remove rejection witness
                        Path(f"{fname}.rej").unlink()
            # Trigger recursive removal of deleted files in last template version
            _remove_old_files(subproject_top, compared)

        # Run post-migration tasks
        self._execute_tasks(
            self.template.migration_tasks("after", self.subproject.template)
        )

    def _git_initialize_repo(self):
        """Initialize a git repository in the current directory."""
        git("init", retcode=None)
        git("add", ".")
        git("config", "user.name", "Copier")
        git("config", "user.email", "copier@copier")
        # 1st commit could fail if any pre-commit hook reformats code
        # 2nd commit uses --no-verify to disable pre-commit-like checks
        git("commit", "--allow-empty", "-am", "dumb commit 1", retcode=None)
        git("commit", "--allow-empty", "-am", "dumb commit 2", "--no-verify")
        git("config", "--unset", "user.name")
        git("config", "--unset", "user.email")


def run_copy(
    src_path: str,
    dst_path: StrOrPath = ".",
    data: Optional[AnyByStrDict] = None,
    **kwargs,
) -> Worker:
    """Copy a template to a destination, from zero.

    This is a shortcut for [run_copy][copier.main.Worker.run_copy].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if data is not None:
        kwargs["data"] = data
    with Worker(src_path=src_path, dst_path=Path(dst_path), **kwargs) as worker:
        worker.run_copy()
    return worker


def run_update(
    dst_path: StrOrPath = ".",
    data: Optional[AnyByStrDict] = None,
    **kwargs,
) -> Worker:
    """Update a subproject, from its template.

    This is a shortcut for [run_update][copier.main.Worker.run_update].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if data is not None:
        kwargs["data"] = data
    with Worker(dst_path=Path(dst_path), **kwargs) as worker:
        worker.run_update()
    return worker


def run_auto(
    src_path: OptStr = None,
    dst_path: StrOrPath = ".",
    data: Optional[AnyByStrDict] = None,
    **kwargs,
) -> Worker:
    """Generate or update a subproject.

    This is a shortcut for [run_auto][copier.main.Worker.run_auto].

    See [Worker][copier.main.Worker] fields to understand this function's args.
    """
    if src_path is None:
        return run_update(dst_path, data, **kwargs)
    return run_copy(src_path, dst_path, data, **kwargs)


def _remove_old_files(prefix: Path, cmp: dircmp, rm_common: bool = False):
    """Remove files and directories only found in "old" template.

    This is an internal helper method used to process a comparison of 2
    directories, where the left one is considered the "old" one, and the
    right one is the "new" one.

    Then, it will recursively try to remove anything that is only in the old
    directory.

    Args:
        prefix:
            Where we start removing. It can be different from the directories
            being compared.
        cmp:
            The comparison result.
        rm_common:
            Should we remove common files and directories?
    """
    # Gather files and dirs to remove
    to_rm = []
    subdirs = {}
    with suppress(NotADirectoryError, FileNotFoundError):
        to_rm = cmp.left_only
        if rm_common:
            to_rm += cmp.common_files + cmp.common_dirs
        subdirs = cmp.subdirs
    # Remove files found only in old template copy
    for name in to_rm:
        target = prefix / name
        if target.is_file():
            target.unlink()
        else:
            # Recurse in dirs totally removed in latest template
            _remove_old_files(target, dircmp(Path(cmp.left, name), target), True)
            # Remove subdir if it ends empty
            with suppress(OSError):
                target.rmdir()  # Raises if dir not empty
    # Recurse
    for key, value in subdirs.items():
        subdir = prefix / key
        _remove_old_files(subdir, value)
        # Remove subdir if it ends empty
        with suppress(OSError):
            subdir.rmdir()  # Raises if dir not empty
