"""Custom exceptions used by Copier."""

from pathlib import Path

from copier.types import PathSeq

from .tools import printf_exception


class UserMessageError(Exception):
    """Exit the program giving a message to the user."""


class UnsupportedVersionError(UserMessageError):
    """Copier version does not support template version."""


class ConfigFileError(ValueError):
    """Parent class defining problems with the config file."""


class InvalidConfigFileError(ConfigFileError):
    """Indicates that the config file is wrong."""

    def __init__(self, conf_path: Path, quiet: bool):
        msg = str(conf_path)
        printf_exception(self, "INVALID CONFIG FILE", msg=msg, quiet=quiet)
        super().__init__(msg)


class MultipleConfigFilesError(ConfigFileError):
    """Both copier.yml and copier.yaml found, and that's an error."""

    def __init__(self, conf_paths: PathSeq, quiet: bool):
        msg = str(conf_paths)
        printf_exception(self, "MULTIPLE CONFIG FILES", msg=msg, quiet=quiet)
        super().__init__(msg)


class InvalidTypeError(TypeError):
    """The question type is not among the supported ones."""
