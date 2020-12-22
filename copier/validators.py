from pathlib import Path

from pydantic.errors import _PathValueError


class PathNotAbsoluteError(_PathValueError):
    code = "path.not_absolute"
    msg_template = '"{path}" is not an absolute path'


def path_is_absolute(value: Path) -> Path:
    if not value.is_absolute():
        raise PathNotAbsoluteError(path=value)
    return value
