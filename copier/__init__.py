"""Copier.

Docs: https://copier.readthedocs.io/
"""

from typing import TYPE_CHECKING, Any

from . import _main
from ._deprecation import deprecate_member_as_internal

if TYPE_CHECKING:
    from ._main import *  # noqa: F403

# This version is a placeholder autoupdated by poetry-dynamic-versioning
__version__ = "0.0.0"


def __getattr__(name: str) -> Any:
    if not name.startswith("_") and name not in {
        "run_copy",
        "run_recopy",
        "run_update",
    }:
        deprecate_member_as_internal(name, __name__)
    return getattr(_main, name)
