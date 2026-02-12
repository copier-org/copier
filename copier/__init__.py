"""Copier.

Docs: https://copier.readthedocs.io/
"""

import importlib.metadata
from typing import TYPE_CHECKING, Any

from . import _main, _types
from ._deprecation import deprecate_member, deprecate_member_as_internal

if TYPE_CHECKING:
    from ._main import *  # noqa: F403
    from ._types import VcsRef  # noqa: F401

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"


def __getattr__(name: str) -> Any:
    if name == "VcsRef":
        deprecate_member(name, __name__, f"{__name__}.types.{name}")
        return getattr(_types, name)

    if not name.startswith("_") and name not in {
        "run_copy",
        "run_recopy",
        "run_update",
    }:
        deprecate_member_as_internal(name, __name__)
    return getattr(_main, name)


__all__ = [
    "run_copy",  # noqa: F405
    "run_recopy",  # noqa: F405
    "run_update",  # noqa: F405
]
