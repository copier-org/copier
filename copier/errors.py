"""Custom exceptions used by Copier."""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic.errors import _PathValueError

from .tools import printf_exception
from .types import PathSeq

if TYPE_CHECKING:  # always false
    from .template import Template
    from .user_data import AnswersMap, Question


# Errors
class CopierError(Exception):
    """Base class for all other Copier errors."""


class UserMessageError(CopierError):
    """Exit the program giving a message to the user."""


class UnsupportedVersionError(UserMessageError):
    """Copier version does not support template version."""


class ConfigFileError(ValueError, CopierError):
    """Parent class defining problems with the config file."""


class InvalidConfigFileError(ConfigFileError):
    """Indicates that the config file is wrong."""

    def __init__(self, conf_path: Path, quiet: bool):
        msg = str(conf_path)
        printf_exception(self, "INVALID CONFIG FILE", msg=msg, quiet=quiet)
        super().__init__(msg)


class MultipleConfigFilesError(ConfigFileError):
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


class ExtensionNotFoundError(UserMessageError):
    """Extensions listed in the configuration could not be loaded."""


class CopierAnswersInterrupt(CopierError, KeyboardInterrupt):
    """CopierAnswersInterrupt is raised during interactive question prompts.

    It typically follows a KeyboardInterrupt (i.e. ctrl-c) and provides an
    opportunity for the caller to conduct additional cleanup, such as writing
    the partially completed answers to a file.

    Attributes:
        answers:
            AnswersMap that contains the partially completed answers object.

        last_question:
            Question representing the last_question that was asked at the time
            the interrupt was raised.

        template:
            Template that was being processed for answers.

    """

    def __init__(
        self, answers: "AnswersMap", last_question: "Question", template: "Template"
    ) -> None:
        self.answers = answers
        self.last_question = last_question
        self.template = template


# Warnings
class CopierWarning(Warning):
    """Base class for all other Copier warnings."""


class UnknownCopierVersionWarning(UserWarning, CopierWarning):
    """Cannot determine installed Copier version."""


class OldTemplateWarning(UserWarning, CopierWarning):
    """Template was designed for an older Copier version."""


class DirtyLocalWarning(UserWarning, CopierWarning):
    """Changes and untracked files present in template."""
