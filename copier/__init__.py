"""Copier.

Docs: https://copier.readthedocs.io/
"""

import importlib.metadata
from typing import TYPE_CHECKING, Any

from . import _main
from ._deprecation import deprecate_member_as_internal
from ._settings import Settings, load_settings
from ._types import Phase, VcsRef

if TYPE_CHECKING:
    from ._main import *  # noqa: F403

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"


def __getattr__(name: str) -> Any:
    if not name.startswith("_") and name not in {
        "run_adopt",
        "run_copy",
        "run_recopy",
        "run_update",
    }:
        deprecate_member_as_internal(name, __name__)
    return getattr(_main, name)


__all__ = [
    "load_settings",
    "run_copy",  # noqa: F405
    "run_recopy",  # noqa: F405
    "run_update",  # noqa: F405,
    "Phase",
    "Settings",
    "VcsRef",
]
