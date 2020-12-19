"""Models representing execution context of Copier."""
import os
from contextlib import suppress
from copy import deepcopy
from functools import cached_property, lru_cache
from pathlib import Path
from typing import (
    Any,
    Callable,
    ChainMap,
    ChainMap as t_ChainMap,
    Literal,
    Mapping,
    Optional,
)
from unicodedata import normalize

import pathspec
import yaml
from jinja2.loaders import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from plumbum.cmd import git
from plumbum.machines import local
from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field, PrivateAttr

from copier.config.factory import filter_config, verify_minimum_version
from copier.config.objects import DEFAULT_DATA, DEFAULT_EXCLUDE, EnvOps
from copier.config.user_data import Question, Questionary, load_config_data
from copier.tools import create_path_filter, to_nice_yaml
from copier.types import (
    AnyByStrDict,
    JSONSerializable,
    OptStr,
    PathSeq,
    StrOrPath,
    StrSeq,
)

from .vcs import clone, get_repo, is_git_repo_root


class AnswersMap(BaseModel):
    init: AnyByStrDict = Field(default_factory=dict)
    user: AnyByStrDict = Field(default_factory=dict)
    last: AnyByStrDict = Field(default_factory=dict)
    default: AnyByStrDict = Field(default_factory=dict)

    # Private
    _local: AnyByStrDict = PrivateAttr(default_factory=dict)

    class Config:
        keep_untouched = (cached_property,)

    @validator(
        "init",
        "user",
        "last",
        "default",
        allow_reuse=True,
        pre=True,
        each_item=True,
    )
    def _deep_copy_answers(cls, v: AnyByStrDict) -> AnyByStrDict:
        """Make sure all dicts are copied."""
        return deepcopy(v)

    @cached_property
    def combined(self) -> t_ChainMap[str, Any]:
        """Answers combined from different sources, sorted by priority."""
        return ChainMap(
            self._local,
            self.user,
            self.init,
            self.last,
            self.default,
            DEFAULT_DATA,
        )

    def old_commit(self) -> OptStr:
        return self.last.get("_commit")


class Template(BaseModel):
    url: str
    ref: OptStr

    class Config:
        allow_mutation = False
        keep_untouched = (cached_property,)

    @cached_property
    def _raw_config(self) -> AnyByStrDict:
        result = load_config_data(self.local_path)
        with suppress(KeyError):
            verify_minimum_version(result["_min_copier_version"])
        return result

    @cached_property
    def commit(self) -> OptStr:
        if self.vcs == "git":
            with local.cwd(self.local_path):
                return git("describe", "--tags", "--always").strip()

    @cached_property
    def default_answers(self) -> AnyByStrDict:
        return {key: value.get("default") for key, value in self.questions_data.items()}

    @cached_property
    def config_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[0]

    @cached_property
    def questions_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[1]

    @cached_property
    def local_path(self) -> Path:
        if self.vcs == "git" and not is_git_repo_root(self.url_expanded):
            return Path(clone(self.url_expanded, self.ref))
        return Path(self.url)

    @cached_property
    def url_expanded(self) -> str:
        return get_repo(self.url) or self.url

    @cached_property
    def vcs(self) -> Optional[Literal["git"]]:
        if get_repo(self.url):
            return "git"


class Subproject(BaseModel):
    local_path: Path
    answers_relpath: Path = Path(".copier-answers.yml")

    class Config:
        keep_untouched = (cached_property,)

    def is_dirty(self) -> bool:
        if self.vcs == "git":
            with local.cwd(self.local_path):
                return bool(git("status", "--porcelain").strip())
        return False

    @cached_property
    def _raw_answers(self) -> AnyByStrDict:
        try:
            return yaml.safe_load((self.local_path / self.answers_relpath).read_text())
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
        last_url = self._raw_answers.get("_src_path")
        last_ref = self._raw_answers.get("_commit")
        if last_url:
            return Template(url=last_url, ref=last_ref)

    @cached_property
    def vcs(self) -> Optional[Literal["git"]]:
        if is_git_repo_root(self.local_path):
            return "git"


class Worker(BaseModel):
    answers_file: Path = Field(".copier-answers.yml")
    cleanup_on_error: bool = True
    data: AnyByStrDict = Field(default_factory=dict)
    dst_path: Path = Field(".")
    envops: EnvOps = Field(default_factory=EnvOps)
    exclude: StrSeq = ()
    extra_paths: PathSeq = ()
    force: bool = False
    pretend: bool = False
    quiet: bool = False
    skip_if_exists: StrSeq = ()
    src_path: OptStr
    subdirectory: OptStr
    use_prereleases: bool = False
    vcs_ref: OptStr

    class Config:
        allow_mutation = False
        keep_untouched = (cached_property,)

    def _answers_to_remember(self) -> Mapping:
        """Get only answers that will be remembered in the copier answers file."""
        # All internal values must appear first
        answers: AnyByStrDict = {}
        commit = self.template.commit
        src = self.src_path or self.answers.last.get("_src_path")
        for key, value in (("_commit", commit), ("_src_path", src)):
            if value is not None:
                answers[key] = value
        # Other data goes next
        answers.update(
            (k, v)
            for (k, v) in self.answers.combined.items()
            if not k.startswith("_")
            and k not in conf.secret_questions
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )

    def _render_context(self) -> dict:
        # All internal values must appear first
        answers: AnyByStrDict = {
            "_commit": self.answers.last.get("_commit"),
            "_src_path": self.src_path or self.answers.last.get("_src_path"),
        }
        for key in tuple(answers):
            if answers[key] is None:
                del answers[key]
        # Other data goes next
        answers.update(
            (k, v)
            for (k, v) in self.answers.combined.items()
            if not k.startswith("_")
            and k not in conf.secret_questions
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )
        return dict(
            self.answers.combined,
            _copier_answers=answers,
            _copier_conf=conf.copy(deep=True, exclude={"data": {"now", "make_secret"}}),
        )

    @lru_cache
    def _path_matcher(self, patterns: StrSeq) -> Callable[[Path], bool]:
        # TODO Is normalization really needed?
        normalized_patterns = map(normalize, ("NFD",), patterns)
        spec = pathspec.PathSpec.from_lines("gitwildmatch", normalized_patterns)
        return spec.match_file

    @cached_property
    def answers(self) -> AnswersMap:
        return AnswersMap(
            init=self.data,
            last=self.subproject.last_answers,
            default=self.template.default_answers,
        )

    @cached_property
    def all_exclusions(self) -> StrSeq:
        base = self.template.config_data.get("exclude", DEFAULT_EXCLUDE)
        return tuple(base) + tuple(self.exclude)

    @cached_property
    def jinja_env(self) -> SandboxedEnvironment:
        """Return a pre-configured Jinja environment."""
        paths = [str(self.src_path), *map(str, self.extra_paths)]
        loader = FileSystemLoader(paths)
        # We want to minimize the risk of hidden malware in the templates
        # so we use the SandboxedEnvironment instead of the regular one.
        # Of course we still have the post-copy tasks to worry about, but at least
        # they are more visible to the final user.
        env = SandboxedEnvironment(loader=loader, **self.envops.dict())
        default_filters = {"to_nice_yaml": to_nice_yaml}
        env.filters.update(default_filters)
        return env

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

    def render_file(self, fullpath: Path, dst: Path) -> str:
        # TODO Get from main.render_file()
        relpath = fullpath.relative_to(self.src_path).as_posix()
        tpl = self.jinja_env.get_template(str(relpath))
        return tpl.render(**self._render_context())

    def render_folder(self, fullpath: Path) -> None:
        """Recursively render a folder.

        Args:
            fullpath: Folder to be rendered. It must be a full path within the template.
        """
        rendered_parts = []
        for part in fullpath.relative_to(self.template.local_path).parts:
            # Skip folder if any part is rendered as an empty string
            part = self.render_string(part)
            if not part:
                return
            rendered_parts.append(part)
        dst_path = Path(self.subproject.local_path, *rendered_parts)
        # TODO

    def render_string(self, string: str) -> str:
        tpl = self.jinja_env.from_string(string)
        return tpl.render(**self._render_context())

    @cached_property
    def subproject(self) -> Subproject:
        return Subproject(local_path=self.dst_path, answers_relpath=self.answers_file)

    @cached_property
    def template(self) -> Template:
        if self.src_path:
            return Template(url=str(self.src_path), ref=self.vcs_ref)
        last_template = self.subproject.template
        if last_template is None:
            raise TypeError("Template not found")
        return last_template

    # Main operations
    def run_auto(self) -> None:
        if self.src_path:
            return self.run_copy()
        return self.run_update()

    def run_copy(self) -> None:
        """Generate a subproject from zero, ignoring what was in the folder."""
        # TODO REFACTOR
        must_exclude = self._path_matcher(self.all_exclusions)
        must_skip = create_path_filter(self.skip_if_exists)
        if not self.quiet:
            print("")  # padding space

        folder: StrOrPath
        rel_folder: StrOrPath

        src_path = self.template.local_path
        if self.subdirectory is not None:
            src_path /= self.subdirectory

        for folder, sub_dirs, files in os.walk(src_path):
            rel_folder = str(folder).replace(str(src_path), "", 1).lstrip(os.path.sep)
            rel_folder = self.render_string(rel_folder)
            rel_folder = str(rel_folder).replace("." + os.path.sep, ".", 1)

            if must_exclude(rel_folder):
                # Folder is excluded, so stop walking it
                sub_dirs[:] = []
                continue

            folder = Path(folder)
            rel_folder = Path(rel_folder)

            render_folder(rel_folder, conf)

            source_paths = get_source_paths(
                conf, folder, rel_folder, files, render, must_exclude
            )
            for source_path, rel_path in source_paths:
                render_file(conf, rel_path, source_path, render, must_skip)

        if not conf.quiet:
            print("")  # padding space

        run_tasks(
            conf,
            render,
            [{"task": t, "extra_env": {"STAGE": "task"}} for t in conf.tasks],
        )
        if not conf.quiet:
            print("")  # padding space

    def run_update(self) -> None:
        from copier.main import update_diff

        return update_diff(self_patched())
