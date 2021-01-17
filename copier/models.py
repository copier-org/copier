"""Models representing execution context of Copier."""
import subprocess
import sys
import tempfile
from collections import ChainMap
from contextlib import suppress
from dataclasses import field, replace
from functools import cached_property
from pathlib import Path
from shutil import rmtree
from typing import (
    Any,
    Callable,
    ChainMap as t_ChainMap,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
)
from unicodedata import normalize

import pathspec
import yaml
from jinja2.loaders import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from packaging.version import InvalidVersion, Version, parse
from plumbum import ProcessExecutionError, colors
from plumbum.cli.terminal import ask
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass

from copier.config.factory import filter_config, verify_minimum_version
from copier.config.objects import (
    DEFAULT_DATA,
    DEFAULT_EXCLUDE,
    DEFAULT_TEMPLATES_SUFFIX,
    EnvOps,
    UserMessageError,
)
from copier.config.user_data import (
    Question,
    Questionary,
    load_config_data,
    query_user_data,
)
from copier.tools import Style, printf, to_nice_yaml
from copier.types import (
    AbsolutePath,
    AnyByStrDict,
    JSONSerializable,
    OptStr,
    RelativePath,
    StrSeq,
)

from .vcs import clone, get_repo, is_git_repo_root


@dataclass
class AnswersMap:
    default: AnyByStrDict = field(default_factory=dict)
    init: AnyByStrDict = field(default_factory=dict)
    last: AnyByStrDict = field(default_factory=dict)
    metadata: AnyByStrDict = field(default_factory=dict)
    user: AnyByStrDict = field(default_factory=dict)

    # Private
    local: AnyByStrDict = field(default_factory=dict, init=False)

    @cached_property
    def combined(self) -> t_ChainMap[str, Any]:
        """Answers combined from different sources, sorted by priority."""
        return ChainMap(
            self.local,
            self.user,
            self.init,
            self.metadata,
            self.last,
            self.default,
            DEFAULT_DATA,
        )

    def old_commit(self) -> OptStr:
        return self.last.get("_commit")


@dataclass
class Template:
    url: str
    ref: OptStr

    @cached_property
    def _raw_config(self) -> AnyByStrDict:
        result = load_config_data(self.local_abspath)
        with suppress(KeyError):
            verify_minimum_version(result["_min_copier_version"])
        return result

    @cached_property
    def answers_relpath(self) -> Path:
        result = Path(self.config_data.get("answers_file", ".copier-answers.yml"))
        assert not result.is_absolute()
        return result

    @cached_property
    def commit(self) -> OptStr:
        if self.vcs == "git":
            with local.cwd(self.local_abspath):
                return git("describe", "--tags", "--always").strip()

    @cached_property
    def default_answers(self) -> AnyByStrDict:
        return {key: value.get("default") for key, value in self.questions_data.items()}

    @cached_property
    def config_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[0]

    @cached_property
    def metadata(self) -> AnyByStrDict:
        result: AnyByStrDict = {"_src_path": self.url}
        if self.commit:
            result["_commit"] = self.commit
        return result

    def migration_tasks(self, stage: str, from_: str, to: str) -> Sequence[Mapping]:
        """Get migration objects that match current version spec.

        Versions are compared using PEP 440.
        """
        result: List[dict] = []
        if not from_ or not to:
            return result
        parsed_from = parse(from_)
        parsed_to = parse(to)
        extra_env = {
            "STAGE": stage,
            "VERSION_FROM": from_,
            "VERSION_TO": to,
        }
        migration: dict
        for migration in self._raw_config.get("_migrations", []):
            if parsed_to >= parse(migration["version"]) > parsed_from:
                extra_env = dict(extra_env, VERSION_CURRENT=str(migration["version"]))
                result += [
                    {"task": task, "extra_env": extra_env}
                    for task in migration.get(stage, [])
                ]
        return result

    @cached_property
    def questions_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[1]

    @cached_property
    def secret_questions(self) -> Set[str]:
        result = set(self.config_data.get("secret_questions", {}))
        for key, value in self.questions_data.items():
            if value.get("secret"):
                result.add(key)
        return result

    @cached_property
    def subdirectory(self) -> str:
        return self.config_data.get("subdirectory", "")

    @cached_property
    def tasks(self) -> Sequence:
        return self.config_data.get("tasks", [])

    @cached_property
    def templates_suffix(self) -> str:
        return self.config_data.get("templates_suffix", DEFAULT_TEMPLATES_SUFFIX)

    @cached_property
    def local_abspath(self) -> Path:
        result = Path(self.url)
        if self.vcs == "git":
            result = Path(clone(self.url_expanded, self.ref))
        if not result.is_dir():
            raise ValueError("Local template must be a directory.")
        return result.absolute()

    @cached_property
    def url_expanded(self) -> str:
        return get_repo(self.url) or self.url

    @cached_property
    def vcs(self) -> Optional[Literal["git"]]:
        if get_repo(self.url):
            return "git"


@dataclass
class Subproject:
    local_abspath: AbsolutePath
    answers_relpath: Path = Path(".copier-answers.yml")

    def is_dirty(self) -> bool:
        if self.vcs == "git":
            with local.cwd(self.local_abspath):
                return bool(git("status", "--porcelain").strip())
        return False

    @property
    def _raw_answers(self) -> AnyByStrDict:
        try:
            return yaml.safe_load(
                (self.local_abspath / self.answers_relpath).read_text()
            )
        except OSError:
            return {}

    @cached_property
    def last_answers(self) -> AnyByStrDict:
        return {
            key: value
            for key, value in self._raw_answers.items()
            if key in {"_src_path", "_commit"} or not key.startswith("_")
        }

    @cached_property
    def template(self) -> Optional[Template]:
        raw_answers = self._raw_answers
        last_url = raw_answers.get("_src_path")
        last_ref = raw_answers.get("_commit")
        if last_url:
            return Template(url=last_url, ref=last_ref)

    @cached_property
    def vcs(self) -> Optional[Literal["git"]]:
        if is_git_repo_root(self.local_abspath):
            return "git"


@dataclass
class Worker:
    answers_file: Optional[RelativePath] = None
    cleanup_on_error: bool = True
    data: AnyByStrDict = field(default_factory=dict)
    dst_path: Path = field(default=".")
    envops: EnvOps = field(default_factory=EnvOps)
    exclude: StrSeq = ()
    force: bool = False
    pretend: bool = False
    quiet: bool = False
    skip_if_exists: StrSeq = ()
    src_path: OptStr = None
    use_prereleases: bool = False
    vcs_ref: OptStr = None

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
                task_cmd = self.render_string(task_cmd)
            else:
                task_cmd = [self.render_string(str(part)) for part in task_cmd]
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
        # Backwards compatibility
        # FIXME Remove it?
        self_conf = replace(self, answers_file=self.answers_relpath)
        return dict(
            DEFAULT_DATA,
            **self.answers.combined,
            _copier_answers=self._answers_to_remember(),
            _copier_conf=self_conf,
        )

    def _path_matcher(self, patterns: StrSeq) -> Callable[[Path], bool]:
        # TODO Is normalization really needed?
        normalized_patterns = (normalize("NFD", pattern) for pattern in patterns)
        spec = pathspec.PathSpec.from_lines("gitwildmatch", normalized_patterns)
        return spec.match_file

    def _solve_render_conflict(self, dst_relpath: Path):
        assert not dst_relpath.is_absolute()
        printf(
            "conflict",
            dst_relpath,
            style=Style.DANGER,
            quiet=self.quiet,
            file_=sys.stderr,
        )
        if self.force:
            return True
        return bool(ask(f" Overwrite {dst_relpath}?", default=True))

    def _render_allowed(
        self, dst_relpath: Path, is_dir: bool = False, expected_contents: bytes = b""
    ) -> bool:
        assert not dst_relpath.is_absolute()
        assert not expected_contents or not is_dir, "Dirs cannot have expected content"
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if dst_relpath != Path("."):
            if self.match_exclude(dst_relpath):
                return False
            if self.match_skip(dst_relpath) and dst_abspath.exists():
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
        except IsADirectoryError:
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
        user = query_user_data(
            questions_data=self.template.questions_data,
            last_answers_data=self.subproject.last_answers,
            forced_answers_data=self.data,
            default_answers_data=self.template.default_answers,
            ask_user=not self.force,
            jinja_env=self.jinja_env,
        )
        return AnswersMap(
            default=self.template.default_answers,
            init=self.data,
            last=self.subproject.last_answers,
            metadata=self.template.metadata,
            user=user,
        )

    @cached_property
    def answers_relpath(self) -> Path:
        return self.answers_file or self.template.answers_relpath

    @cached_property
    def all_exclusions(self) -> StrSeq:
        base = self.template.config_data.get("exclude", DEFAULT_EXCLUDE)
        return tuple(base) + tuple(self.exclude)

    @cached_property
    def jinja_env(self) -> SandboxedEnvironment:
        """Return a pre-configured Jinja environment."""
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
        return self._path_matcher(self.all_exclusions)

    @cached_property
    def match_skip(self) -> Callable[[Path], bool]:
        return self._path_matcher(map(self.render_string, self.skip_if_exists))

    @cached_property
    def questionary(self) -> Questionary:
        result = Questionary(
            answers_default=self.answers.default,
            answers_forced=self.answers.init,
            answers_last=self.answers.last,
            answers_user=self.answers.user,
            ask_user=not self.force,
            env=self.jinja_env,
        )
        for question, details in self.template.questions_data.items():
            # TODO Append explicitly?
            Question(var_name=question, questionary=result, **details)
        return result

    def render_file(self, src_abspath: Path) -> None:
        # TODO Get from main.render_file()
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self.render_path(src_relpath)
        if dst_relpath is None:
            return
        if src_abspath.name.endswith(self.template.templates_suffix):
            tpl = self.jinja_env.get_template(str(src_relpath))
            new_content = tpl.render(**self._render_context()).encode()
        else:
            new_content = src_abspath.read_bytes()
        if not self._render_allowed(dst_relpath, expected_contents=new_content):
            return
        if not self.pretend:
            dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
            dst_abspath.write_bytes(new_content)

    def render_folder(self, src_abspath: Path) -> None:
        """Recursively render a folder.

        Args:
            src_path:
                Folder to be rendered. It must be an absolute path within
                the template.
        """
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self.render_path(src_relpath)
        if dst_relpath is None:
            return
        if not self._render_allowed(dst_relpath, is_dir=True):
            return
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if not self.pretend:
            dst_abspath.mkdir(exist_ok=True)
        for file in src_abspath.iterdir():
            if file.is_dir():
                self.render_folder(file)
            else:
                self.render_file(file)

    def render_path(self, relpath: Path) -> Optional[Path]:
        is_template = relpath.name.endswith(self.template.templates_suffix)
        templated_sibling = (
            self.template.local_abspath / f"{relpath}{self.template.templates_suffix}"
        )
        if templated_sibling.exists():
            return None
        rendered_parts = []
        for part in relpath.parts:
            # Skip folder if any part is rendered as an empty string
            part = self.render_string(part)
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

    def render_string(self, string: str) -> str:
        tpl = self.jinja_env.from_string(string)
        return tpl.render(**self._render_context())

    @cached_property
    def subproject(self) -> Subproject:
        return Subproject(
            local_abspath=self.dst_path,
            answers_relpath=self.answers_file or ".copier-answers.yml",
        )

    @cached_property
    def template(self) -> Template:
        url = self.src_path
        if not url:
            if self.subproject.template is None:
                raise TypeError("Template not found")
            url = self.subproject.template.url
        return Template(url=url, ref=self.vcs_ref)

    @cached_property
    def template_copy_root(self) -> Path:
        subdir = self.render_string(self.template.subdirectory) or ""
        return self.template.local_abspath / subdir

    # Main operations
    def run_auto(self) -> None:
        if self.src_path:
            return self.run_copy()
        return self.run_update()

    def run_copy(self) -> None:
        """Generate a subproject from zero, ignoring what was in the folder."""
        was_existing = self.subproject.local_abspath.exists()
        if not self.quiet:
            # TODO Unify printing tools
            print("")  # padding space
        src_abspath = self.template_copy_root
        try:
            self.render_folder(src_abspath)
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
        """Update the subproject."""
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
        with tempfile.TemporaryDirectory(prefix=f"{__name__}.update_diff.") as dst_temp:
            old_worker = self.copy(
                update={
                    "dst_path": dst_temp,
                    "data": self.answers.last,
                    "force": True,
                    "quiet": True,
                    "src_path": self.subproject.template.url,
                    "vcs_ref": self.subproject.template.commit,
                },
                deep=True,
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
        del self.subproject.last_answers
        del self.answers
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
