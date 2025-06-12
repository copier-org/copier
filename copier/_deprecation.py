"""Deprecation utilities."""

from __future__ import annotations

import warnings

_issue_note = (
    "If you have any questions or concerns, please raise an issue at "
    "<https://github.com/copier-org/copier/issues>."
)


def deprecate_module_as_internal(name: str) -> None:
    """Deprecate a module as internal with a warning.

    Args:
        name: The module name.
    """
    warnings.warn(
        f"Importing from `{name}` is deprecated. This module is intended for internal "
        f"use only and will become inaccessible in the future. {_issue_note}",
        DeprecationWarning,
        stacklevel=3,
    )


def deprecate_member_as_internal(member: str, module: str) -> None:
    """Deprecate a module member as internal with a warning.

    Args:
        member: The module member name.
        module: The module name.
    """
    warnings.warn(
        f"Importing `{member}` from `{module}` is deprecated. This module member is "
        "intended for internal use only and will become inaccessible in the future. "
        f"{_issue_note}",
        DeprecationWarning,
        stacklevel=3,
    )


def deprecate_member(member: str, module: str, new_import: str) -> None:
    """Deprecate a module member with a new import statement with a warning.

    Args:
        member: The module member name.
        module: The module name.
        new_import: The new import statement.
    """
    warnings.warn(
        f"Importing `{member}` from `{module}` is deprecated. Please update the import "
        f"to `{new_import}`. The deprecated import will become invalid in the future. "
        f"{_issue_note}",
        DeprecationWarning,
        stacklevel=3,
    )


def deprecate_answers_file_template_path() -> None:
    """Deprecate answers file template paths other than the template's root directory."""
    warnings.warn(
        "Answers file template locations other than the template root directory are "
        "deprecated. Specify a non-default answers file name/location via the "
        "`_answers_file` setting in the `copier.yaml` file instead. "
        f"{_issue_note}",
        DeprecationWarning,
        stacklevel=3,
    )
