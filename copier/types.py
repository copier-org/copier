"""Deprecated: module is intended for internal use only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copier import _types
from copier._deprecation import deprecate_member_as_internal

if TYPE_CHECKING:
    from copier._types import *  # noqa: F403


def __getattr__(name: str) -> Any:
    if not name.startswith("_") and name not in {"Phase", "VcsRef"}:
        deprecate_member_as_internal(name, __name__)
    return getattr(_types, name)
