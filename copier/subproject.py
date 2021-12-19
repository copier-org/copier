"""Objects to interact with subprojects.

A *subproject* is a project that gets rendered and/or updated with Copier.
"""

import sys
from pathlib import Path
from typing import Optional

import yaml
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass

from .template import Template
from .types import AbsolutePath, AnyByStrDict, VCSTypes
from .vcs import is_in_git_repo

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property


@dataclass
class Subproject:
    """Object that represents the subproject and its current state.

    Attributes:
        local_abspath:
            Absolute path on local disk pointing to the subproject root folder.

        answers_relpath:
            Relative path to [the answers file][the-copier-answersyml-file].
    """

    local_abspath: AbsolutePath
    answers_relpath: Path = Path(".copier-answers.yml")

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
        """The last answers, loaded raw as yaml."""
        try:
            return yaml.safe_load(
                (self.local_abspath / self.answers_relpath).read_text()
            )
        except OSError:
            return {}

    @cached_property
    def last_answers(self) -> AnyByStrDict:
        """Last answers, excluding private ones (except _src_path and _commit)."""
        return {
            key: value
            for key, value in self._raw_answers.items()
            if key in {"_src_path", "_commit"} or not key.startswith("_")
        }

    @cached_property
    def template(self) -> Optional[Template]:
        """Template, as it was used the last time."""
        last_url = self.last_answers.get("_src_path")
        last_ref = self.last_answers.get("_commit")
        if last_url:
            return Template(url=last_url, ref=last_ref)

    @cached_property
    def vcs(self) -> Optional[VCSTypes]:
        """VCS type of the subproject."""
        if is_in_git_repo(self.local_abspath):
            return "git"
