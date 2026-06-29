"""User settings models and helper functions."""

from __future__ import annotations

import os
import posixpath
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from os.path import expanduser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

import yaml
from platformdirs import user_config_path
from pydantic import BaseModel, Field, ValidationError

from ._tools import OS
from .errors import MissingSettingsWarning, SettingsError

_ENV_VAR = "COPIER_SETTINGS_PATH"


@dataclass(frozen=True, slots=True)
class Settings:
    """User settings."""

    defaults: Mapping[str, Any] = field(default_factory=dict)
    """Default values for questions."""

    trust: Sequence[str] = field(default_factory=list)
    """Set of trusted repositories or prefixes."""


def load_settings(settings_path: Path | None = None) -> Settings:
    """Load settings from a YAML file.

    If `settings_path` is not given, the path is determined from the
    `COPIER_SETTINGS_PATH` environment variable or the platform-specific
    default configuration directory.

    Args:
        settings_path: Path to a settings YAML file.

    Returns:
        Settings loaded from the YAML file.

    Raises:
        SettingsError: If the settings file is invalid.
    """
    try:
        settings = SettingsModel.from_file(settings_path)
    except yaml.YAMLError as e:
        raise SettingsError(f"Invalid YAML data: {e}") from e
    except ValidationError as e:
        message = "\n".join(
            f"  {'.'.join(map(str, err['loc']))}:\n    {err['msg']}"
            for err in e.errors()
        )
        raise SettingsError(f"Invalid format:\n{message}") from e
    return Settings(defaults=settings.defaults, trust=list(settings.trust))


def is_trusted_repository(trust: Iterable[str], repository: str) -> bool:
    """Check if a repository is trusted.

    Args:
        trust: The set of trusted repositories or prefixes.
        repository: The repository URL to check.

    Returns:
        Whether the repository is trusted.
    """
    return _is_trusted(trust, repository)


class SettingsModel(BaseModel):
    """User settings model."""

    defaults: dict[str, Any] = Field(
        default_factory=dict, description="Default values for questions"
    )
    trust: set[str] = Field(
        default_factory=set, description="List of trusted repositories or prefixes"
    )

    @staticmethod
    def _default_settings_path() -> Path:
        return _default_settings_path()

    @classmethod
    def from_file(cls, settings_path: Path | None = None) -> SettingsModel:
        """Load settings from a file."""
        env_path = os.getenv(_ENV_VAR)
        if settings_path is None:
            if env_path:
                settings_path = Path(env_path)
            else:
                settings_path = cls._default_settings_path()

                # NOTE: Remove after a sufficiently long deprecation period.
                if OS == "windows":
                    old_settings_path = user_config_path("copier") / "settings.yml"
                    if old_settings_path.is_file():
                        warnings.warn(
                            f"Settings path {old_settings_path} is deprecated. "
                            f"Please migrate to {settings_path}.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        settings_path = old_settings_path
        if settings_path.is_file():
            data = yaml.safe_load(settings_path.read_bytes())
            return cls.model_validate(data)
        elif env_path:
            warnings.warn(
                f"Settings file not found at {env_path}", MissingSettingsWarning
            )
        return cls()

    def is_trusted(self, repository: str) -> bool:
        """Check if a repository is trusted."""
        return _is_trusted(self, repository)

    def normalize(self, url: str) -> str:
        """Normalize an URL using user settings."""
        return _normalize(url)


def _default_settings_path() -> Path:
    return user_config_path("copier", appauthor=False) / "settings.yml"


def _is_trusted(
    trust_or_settings: Iterable[str] | SettingsModel, repository: str
) -> bool:
    trust = (
        trust_or_settings.trust
        if isinstance(trust_or_settings, SettingsModel)
        else trust_or_settings
    )
    normalized_repository = _normalize(repository)
    return any(
        normalized_repository.startswith(_normalize(t))
        if t.endswith("/")
        else normalized_repository == _normalize(t)
        for t in trust
    )


def _normalize(url: str) -> str:
    if url.startswith("~"):  # Only expand on str to avoid messing with URLs
        url = expanduser(url)  # noqa: PTH111
    if "://" in url:
        parts = urlsplit(url)
        # Percent-decode before normalizing so that encoded dot segments (e.g.
        # `%2e%2e`) and encoded separators (e.g. `%2f`) are collapsed by
        # `posixpath.normpath`. Backslashes (literal or `%5c`) are folded to
        # forward slashes because some servers and intermediaries treat them
        # as path separators while `posixpath.normpath` does not. Otherwise
        # the form used for the trust check could differ from what the
        # HTTP/Git layer ultimately resolves, allowing a trust-prefix bypass.
        decoded_path = unquote(parts.path).replace("\\", "/")
        path = posixpath.normpath(decoded_path) if decoded_path else decoded_path
        if decoded_path.endswith("/") and not path.endswith("/"):
            path += "/"
        return urlunsplit(
            (parts.scheme, parts.netloc, path, parts.query, parts.fragment)
        )
    normalized = os.path.normpath(url)
    if url.endswith(("/", os.sep)) and not normalized.endswith(os.sep):
        normalized += os.sep
    return normalized
