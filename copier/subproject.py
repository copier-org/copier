"""Objects to interact with subprojects.

A *subproject* is a project that gets rendered and/or updated with Copier.
"""

from pathlib import Path
from typing import Optional

import yaml
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass

from .template import Template
from .types import AbsolutePath, AnyByStrDict, VCSTypes
from .vcs import is_git_repo_root

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property


@dataclass
class Subproject:
    """Object that represents the subproject and its current state."""

    local_abspath: AbsolutePath
    """Absolute path on local disk pointing to the subproject root folder."""

    answers_relpath: Path = Path(".copier-answers.yml")
    """Relative path to [the answers file](configuring.md#the-answers-file)."""

    def is_dirty(self) -> bool:
        """Indicates if the local template root is dirty.

        Only applicable for VCS-tracked templates.
        """
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
    def vcs(self) -> Optional[VCSTypes]:
        if is_git_repo_root(self.local_abspath):
            return "git"
