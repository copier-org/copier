from pathlib import Path

from pydantic.errors import _PathValueError


class PathNotAbsoluteError(_PathValueError):
    code = "path.not_absolute"
    msg_template = '"{path}" is not an absolute path'


class PathNotRelativeError(_PathValueError):
    code = "path.not_relative"
    msg_template = '"{path}" is not a relative path'


def path_is_absolute(value: Path) -> Path:
    if not value.is_absolute():
        raise PathNotAbsoluteError(path=value)
    return value


def path_is_relative(value: Path) -> Path:
    if not value.is_absolute():
        raise PathNotRelativeError(path=value)
    return value
