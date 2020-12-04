"""Models representing execution context of Copier."""
from contextlib import suppress
from copy import deepcopy
from pathlib import Path
from typing import Any, ChainMap, ChainMap as t_ChainMap, Literal, Optional

import yaml
from lazy import lazy
from plumbum.cmd import git
from plumbum.machines import local
from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field, PrivateAttr

from copier.config.factory import filter_config, verify_minimum_version
from copier.config.objects import DEFAULT_DATA, ConfigData
from copier.config.user_data import load_config_data
from copier.main import copy_local, update_diff
from copier.types import AnyByStrDict

from .vcs import clone, get_repo, is_git_repo_root


class AnswersMap(BaseModel):
    init: AnyByStrDict = Field(default_factory=dict)
    user: AnyByStrDict = Field(default_factory=dict)
    last: AnyByStrDict = Field(default_factory=dict)
    default: AnyByStrDict = Field(default_factory=dict)

    # Private
    _local: AnyByStrDict = PrivateAttr(default_factory=dict)

    @validator(
        "init",
        "user",
        "last",
        "default",
        pre=True,
        each_item=True,
    )
    def dict_copy(cls, v: AnyByStrDict) -> AnyByStrDict:
        """Make sure all dicts are copied."""
        return deepcopy(v)

    @lazy
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

    class Config:
        allow_mutation = False


class Template(BaseModel):
    url: str
    ref: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.ref and self.vcs == "git":
            self.ref = "HEAD"

    @lazy
    def _raw_config(self) -> AnyByStrDict:
        result = load_config_data(self.local_path)
        with suppress(KeyError):
            verify_minimum_version(result["_min_copier_version"])
        return result

    @lazy
    def config_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[0]

    @lazy
    def questions_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[1]

    @lazy
    def local_path(self) -> Path:
        if self.vcs == "git" and not is_git_repo_root(self.url_expanded):
            return Path(clone(self.url_expanded, self.ref))
        return Path(self.url)

    @lazy
    def url_expanded(self) -> str:
        return get_repo(self.url) or self.url

    @lazy
    def vcs(self) -> Optional[Literal["git"]]:
        if get_repo(self.url):
            return "git"


class Subproject(BaseModel):
    local_path: Path
    answers_relpath: Path = Path(".copier-answers.yml")

    def exists(self) -> bool:
        return self.local_path.is_dir()

    def is_dirty(self) -> bool:
        if self.vcs == "git":
            with local.cwd(self.local_path):
                return bool(git("status", "--porcelain").strip())
        return False

    @lazy
    def _raw_answers(self) -> AnyByStrDict:
        try:
            return yaml.safe_load((self.local_path / self.answers_relpath).read_text())
        except OSError:
            return {}

    @lazy
    def template(self) -> Optional[Template]:
        last_url = self._raw_answers.get("_src_path")
        last_ref = self._raw_answers.get("_commit")
        if last_url:
            return Template(url=last_url, ref=last_ref)

    @lazy
    def vcs(self) -> Optional[Literal["git"]]:
        if is_git_repo_root(self.local_path):
            return "git"


class Copier(BaseModel):
    answers: AnswersMap
    conf: ConfigData

    # Properties
    @lazy
    def subproject(self) -> Subproject:
        return Subproject()

    @lazy
    def template(self) -> Template:
        try:
            return Template(url=self.conf.src_path, ref=self.conf.vcs_ref)
        except TypeError:
            return self.subproject.template

    # Main operations
    def run_auto(self) -> None:
        if not self.conf.src_path:
            return self.run_update()
        return self.run_copy()

    def run_copy(self) -> None:
        return copy_local(self.conf)

    def run_update(self) -> None:
        return update_diff(self.conf)
