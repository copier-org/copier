"""Models representing execution context of Copier."""
from contextlib import suppress
from pathlib import Path
from typing import Literal, Optional

from lazy import lazy
from plumbum.cmd import git
from plumbum.machines import local
from pydantic import BaseModel

from copier.config.factory import filter_config, verify_minimum_version
from copier.config.user_data import load_config_data
from copier.types import AnyByStrDict

from .vcs import clone, get_repo, is_git_repo_root


class Template(BaseModel):
    url: str
    ref: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.ref and self.vcs == "git":
            self.ref = "HEAD"

    @lazy
    def _config_raw(self) -> AnyByStrDict:
        result = load_config_data(self.local_path)
        with suppress(KeyError):
            verify_minimum_version(result["_min_copier_version"])
        return result

    @lazy
    def config_data(self) -> AnyByStrDict:
        return filter_config(self._config_raw)[0]

    @lazy
    def questions_data(self) -> AnyByStrDict:
        return filter_config(self._config_raw)[1]

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

    def exists(self) -> bool:
        return self.local_path.is_dir()

    def is_dirty(self) -> bool:
        if self.vcs == "git":
            with local.cwd(self.local_path):
                return bool(git("status", "--porcelain"))
        return False

    @lazy
    def vcs(self) -> Optional[Literal["git"]]:
        if is_git_repo_root(self.local_path):
            return "git"
