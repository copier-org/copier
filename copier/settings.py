"""Deprecated: module is intended for internal use only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copier import _settings
from copier._deprecation import (
    deprecate_member_as_internal,
    deprecate_module_as_internal,
)

if TYPE_CHECKING:
    from copier._settings import (  # noqa: F401
        _ENV_VAR as ENV_VAR,
        SettingsModel as Settings,
    )


deprecate_module_as_internal(__name__)


def __getattr__(name: str) -> Any:
    # Explicitly handle deprecated members with re-mapped names for backwards
    # compatibility.
    if name == "Settings":
        deprecate_member_as_internal(name, __name__)
        return _settings.SettingsModel
    if name == "ENV_VAR":
        deprecate_member_as_internal(name, __name__)
        return _settings._ENV_VAR

    raise AttributeError(f"module {__name__} has no attribute '{name}'")
