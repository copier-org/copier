"""Custom exceptions used by Copier."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

from ._tools import printf_exception
from ._types import PathSeq

if TYPE_CHECKING:  # always false
    from ._template import Template
    from ._user_data import AnswersMap, Question

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self


# Errors
class CopierError(Exception):
    """Base class for all other Copier errors."""


class UserMessageError(CopierError):
    """Exit the program giving a message to the user."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message


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

    def __init__(self, conf_paths: PathSeq):
        msg = str(conf_paths)
        printf_exception(self, "MULTIPLE CONFIG FILES", msg=msg)
        super().__init__(msg)


class InvalidTypeError(TypeError, CopierError):
    """The question type is not among the supported ones."""


class PathError(CopierError, ValueError):
    """The path is invalid in the given context."""


class PathNotAbsoluteError(PathError):
    """The path is not absolute, but it should be."""

    def __init__(self, *, path: Path) -> None:
        super().__init__(f'"{path}" is not an absolute path')


class PathNotRelativeError(PathError):
    """The path is not relative, but it should be."""

    def __init__(self, *, path: Path) -> None:
        super().__init__(f'"{path}" is not a relative path')


class ForbiddenPathError(PathError):
    """The path is forbidden in the given context."""

    def __init__(self, *, path: Path) -> None:
        super().__init__(f'"{path}" is forbidden')


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
        self, answers: AnswersMap, last_question: Question, template: Template
    ) -> None:
        self.answers = answers
        self.last_question = last_question
        self.template = template


class UnsafeTemplateError(CopierError):
    """Unsafe Copier template features are used without explicit consent."""

    def __init__(self, features: Sequence[str]):
        assert features
        s = "s" if len(features) > 1 else ""
        super().__init__(
            f"Template uses potentially unsafe feature{s}: {', '.join(features)}.\n"
            "If you trust this template, consider adding the `--trust` option when running `copier copy/update`."
        )


class YieldTagInFileError(CopierError):
    """A yield tag is used in the file content, but it is not allowed."""


class MultipleYieldTagsError(CopierError):
    """Multiple yield tags are used in one path name, but it is not allowed."""


class TaskError(subprocess.CalledProcessError, UserMessageError):
    """Exception raised when a task fails."""

    def __init__(
        self,
        command: str | Sequence[str],
        returncode: int,
        stdout: str | bytes | None,
        stderr: str | bytes | None,
    ):
        subprocess.CalledProcessError.__init__(
            self, returncode=returncode, cmd=command, output=stdout, stderr=stderr
        )
        message = f"Task {command!r} returned non-zero exit status {returncode}."
        UserMessageError.__init__(self, message)

    @classmethod
    def from_process(
        cls, process: CompletedProcess[str] | CompletedProcess[bytes]
    ) -> Self:
        """Create a TaskError from a CompletedProcess."""
        return cls(
            command=process.args,
            returncode=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )


# Warnings
class CopierWarning(Warning):
    """Base class for all other Copier warnings."""


class UnknownCopierVersionWarning(UserWarning, CopierWarning):
    """Cannot determine installed Copier version."""


class OldTemplateWarning(UserWarning, CopierWarning):
    """Template was designed for an older Copier version."""


class DirtyLocalWarning(UserWarning, CopierWarning):
    """Changes and untracked files present in template."""


class ShallowCloneWarning(UserWarning, CopierWarning):
    """The template repository is a shallow clone."""


class MissingSettingsWarning(UserWarning, CopierWarning):
    """Settings path has been defined but file is missing."""


class MissingFileWarning(UserWarning, CopierWarning):
    """I still couldn't find what I'm looking for."""


class InteractiveSessionError(UserMessageError):
    """An interactive session is required to run this program."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Interactive session required: {message}")
