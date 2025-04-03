"""Deprecated: module is intended for internal use only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copier import _jinja_ext
from copier._deprecation import (
    deprecate_member_as_internal,
    deprecate_module_as_internal,
)

if TYPE_CHECKING:
    from copier._jinja_ext import *  # noqa: F403


deprecate_module_as_internal(__name__)


def __getattr__(name: str) -> Any:
    if not name.startswith("_"):
        deprecate_member_as_internal(name, __name__)
    return getattr(_jinja_ext, name)
