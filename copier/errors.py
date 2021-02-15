"""Custom exceptions used by Copier."""

from pathlib import Path

from pydantic.errors import _PathValueError

from .tools import printf_exception
from .types import PathSeq


# Errors
class CopierError(Exception):
    """Base class for all other Copier errors."""


class UserMessageError(CopierError):
    """Exit the program giving a message to the user."""


class UnsupportedVersionError(UserMessageError, CopierError):
    """Copier version does not support template version."""


class ConfigFileError(ValueError, CopierError):
    """Parent class defining problems with the config file."""


class InvalidConfigFileError(ConfigFileError, CopierError):
    """Indicates that the config file is wrong."""

    def __init__(self, conf_path: Path, quiet: bool):
        msg = str(conf_path)
        printf_exception(self, "INVALID CONFIG FILE", msg=msg, quiet=quiet)
        super().__init__(msg)


class MultipleConfigFilesError(ConfigFileError, CopierError):
    """Both copier.yml and copier.yaml found, and that's an error."""

    def __init__(self, conf_paths: "PathSeq"):
        msg = str(conf_paths)
        printf_exception(self, "MULTIPLE CONFIG FILES", msg=msg)
        super().__init__(msg)


class InvalidTypeError(TypeError, CopierError):
    """The question type is not among the supported ones."""


class PathNotAbsoluteError(_PathValueError, CopierError):
    """The path is not absolute, but it should be."""

    code = "path.not_absolute"
    msg_template = '"{path}" is not an absolute path'


class PathNotRelativeError(_PathValueError, CopierError):
    """The path is not relative, but it should be."""

    code = "path.not_relative"
    msg_template = '"{path}" is not a relative path'


# Warnings
class CopierWarning(Warning):
    """Base class for all other Copier warnings."""


class UnknownCopierVersionWarning(UserWarning, CopierWarning):
    """Cannot determine installed Copier version."""


class OldTemplateWarning(UserWarning, CopierWarning):
    """Template was designed for an older Copier version."""
