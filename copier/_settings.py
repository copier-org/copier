"""User settings models and helper functions."""

from __future__ import annotations

import os
import posixpath
import re
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from os.path import expanduser
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import yaml
from platformdirs import user_config_path
from pydantic import BaseModel, Field, ValidationError

from ._tools import OS
from ._vcs import ALIASES
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
    repository_is_safe = _is_safe_url(repository)
    normalized_repository = _normalize(repository)
    for t in trust:
        if repository_is_safe and _is_safe_url(t):
            if t.endswith("/"):
                # Safe prefix: trust anything nested under it.
                if normalized_repository.startswith(_normalize(t)):
                    return True
            # Safe exact: trust only the exact normalized match.
            elif normalized_repository == _normalize(t):
                return True
        # Unsafe: trust only an exact raw match.
        elif repository == t:
            return True
    return False


# Git's SCP-like syntax: [user@]host:path
_SCP_URL = re.compile(r"^(?:[^/@:\s]+@)?[^/:\s]+:.+$")

# RFC 3986 §2.3 "unreserved" characters: letters, digits, `-`, `.`, `_`, `~`.
_SAFE_URL_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._~-]+$")


def _is_url_style(url: str) -> bool:
    """Whether `url` is an absolute URL or uses one of Copier's alias prefixes."""
    return "://" in url or url.startswith(tuple(ALIASES.keys()))


def _is_scp_style(url: str) -> bool:
    """Whether `url` uses Git's SCP-like syntax (`[user@]host:path`)."""
    return (
        not PureWindowsPath(url).is_absolute() and _SCP_URL.fullmatch(url) is not None
    )


def _is_safe_url(url: str) -> bool:
    """Whether `url` is a local path, or a remote reference with a safe path.

    Local filesystem paths are always considered safe, since percent-encoding has
    no meaning there and a literal backslash is simply the standard, unambiguous
    path separator on Windows. URL paths segments are considered safe if they contain
    only RFC 3986 "unreserved" characters.
    """
    if _is_url_style(url):
        path = urlsplit(url).path
    elif _is_scp_style(url):
        path = url.split(":", 1)[1]
    else:
        return True

    segments = path.split("/")
    if segments and segments[0] == "":
        segments = segments[1:]
    if segments and segments[-1] == "":
        segments = segments[:-1]

    return all(_SAFE_URL_PATH_SEGMENT_RE.fullmatch(segment) for segment in segments)


def _normalize(url: str) -> str:
    """Normalize `url` for trust comparison.

    For URL-style and SCP-style remotes, resolves `.`/`..` path segments using
    POSIX path semantics; see `_normalize_url_path` for why this is not full
    RFC 3986 normalization. For local paths, expands a leading `~` and resolves
    `.`/`..` segments using OS path semantics.
    """
    if _is_url_style(url):
        parts = urlsplit(url)
        path = _normalize_url_path(parts.path)
        return urlunsplit(
            (parts.scheme, parts.netloc, path, parts.query, parts.fragment)
        )

    if _is_scp_style(url):
        host, path = url.split(":", 1)
        path = _normalize_url_path(path)
        return f"{host}:{path}"

    if url.startswith("~"):  # Only expand on str to avoid messing with URLs
        url = expanduser(url)  # noqa: PTH111
    normalized = os.path.normpath(url)
    if url.endswith(("/", os.sep)) and not normalized.endswith(os.sep):
        normalized += os.sep
    return normalized


def _normalize_url_path(path: str) -> str:
    """Resolve `.`/`..` segments and collapse redundant `/` in `path`.

    This uses POSIX path semantics, not RFC 3986 path normalization: in
    particular, it collapses consecutive slashes, which RFC 3986 does not.
    """
    normalized = posixpath.normpath(path) if path else path
    if path.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    return normalized
