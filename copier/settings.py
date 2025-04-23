"""User settings models and helper functions."""

from __future__ import annotations

import os
import warnings
from os.path import expanduser
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_path
from pydantic import BaseModel, Field

from ._tools import OS
from .errors import MissingSettingsWarning

ENV_VAR = "COPIER_SETTINGS_PATH"


class Settings(BaseModel):
    """User settings model."""

    defaults: dict[str, Any] = Field(
        default_factory=dict, description="Default values for questions"
    )
    trust: set[str] = Field(
        default_factory=set, description="List of trusted repositories or prefixes"
    )

    @staticmethod
    def _default_settings_path() -> Path:
        return user_config_path("copier", appauthor=False) / "settings.yml"

    @classmethod
    def from_file(cls, settings_path: Path | None = None) -> Settings:
        """Load settings from a file."""
        env_path = os.getenv(ENV_VAR)
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
        return any(
            repository.startswith(self.normalize(trusted))
            if trusted.endswith("/")
            else repository == self.normalize(trusted)
            for trusted in self.trust
        )

    def normalize(self, url: str) -> str:
        """Normalize an URL using user settings."""
        if url.startswith("~"):  # Only expand on str to avoid messing with URLs
            url = expanduser(url)  # noqa: PTH111
        return url
