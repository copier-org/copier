"""Some utility functions."""

from __future__ import annotations

import errno
import os
import platform
import re
import stat
import sys
from collections.abc import Iterator
from contextlib import suppress
from decimal import Decimal
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Literal, TextIO, TypeVar, cast

import colorama
from packaging.version import Version
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from pydantic import StrictBool

colorama.just_fix_windows_console()


class Style:
    """Common color styles."""

    OK = [colorama.Fore.GREEN, colorama.Style.BRIGHT]
    WARNING = [colorama.Fore.YELLOW, colorama.Style.BRIGHT]
    IGNORE = [colorama.Fore.CYAN]
    DANGER = [colorama.Fore.RED, colorama.Style.BRIGHT]
    RESET = [colorama.Fore.RESET, colorama.Style.RESET_ALL]


INDENT = " " * 2
HLINE = "-" * 42

OS: Literal["linux", "macos", "windows"] | None = cast(
    Any,
    {
        "Linux": "linux",
        "Darwin": "macos",
        "Windows": "windows",
    }.get(platform.system()),
)


def copier_version() -> Version:
    """Get closest match for the installed copier version."""
    # Importing __version__ at the top of the module creates a circular import
    # ("cannot import name '__version__' from partially initialized module 'copier'"),
    # so instead we do a lazy import here
    from . import __version__

    if __version__ != "0.0.0":
        return Version(__version__)

    # Get the installed package version otherwise, which is sometimes more specific
    return Version(version("copier"))


def printf(
    action: str,
    msg: Any = "",
    style: list[str] | None = None,
    indent: int = 10,
    quiet: bool | StrictBool = False,
    file_: TextIO = sys.stdout,
) -> str | None:
    """Print string with common format."""
    if quiet:
        return None
    _msg = str(msg)
    action = action.rjust(indent, " ")
    if not style:
        return action + _msg

    out = style + [action] + Style.RESET + [INDENT, _msg]
    print(*out, sep="", file=file_)
    return None


def printf_exception(
    e: Exception, action: str, msg: str = "", indent: int = 0, quiet: bool = False
) -> None:
    """Print exception with common format."""
    if not quiet:
        print("", file=sys.stderr)
        printf(action, msg=msg, style=Style.DANGER, indent=indent, file_=sys.stderr)
        print(HLINE, file=sys.stderr)
        print(e, file=sys.stderr)
        print(HLINE, file=sys.stderr)


def cast_to_str(value: Any) -> str:
    """Parse anything to str.

    Params:
        value:
            Anything to be casted to a str.
    """
    if isinstance(value, str):
        return value.value if isinstance(value, Enum) else value
    if isinstance(value, (float, int, Decimal)):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    raise ValueError(f"Could not convert {value} to string")


def cast_to_bool(value: Any) -> bool:
    """Parse anything to bool.

    Params:
        value:
            Anything to be casted to a bool. Tries to be as smart as possible.

            1.  Cast to number. Then: 0 = False; anything else = True.
            1.  Find [YAML booleans](https://yaml.org/type/bool.html),
                [YAML nulls](https://yaml.org/type/null.html) or `none` in it
                and use it appropriately.
            1.  Cast to boolean using standard python `bool(value)`.
    """
    # Assume it's a number
    with suppress(TypeError, ValueError):
        return bool(float(value))
    # Assume it's a string
    with suppress(AttributeError):
        lower = value.lower()
        if lower in {"y", "yes", "t", "true", "on"}:
            return True
        elif lower in {"n", "no", "f", "false", "off", "~", "null", "none"}:
            return False
    # Assume nothing
    return bool(value)


def force_str_end(original_str: str, end: str = "\n") -> str:
    """Make sure a `original_str` ends with `end`.

    Params:
        original_str: String that you want to ensure ending.
        end: String that must exist at the end of `original_str`
    """
    if not original_str.endswith(end):
        return original_str + end
    return original_str


def handle_remove_readonly(
    func: Callable[[str], None],
    path: str,
    # TODO: Change this union to simply `BaseException` when Python 3.11 support is dropped
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType],
) -> None:
    """Handle errors when trying to remove read-only files through `shutil.rmtree`.

    On Windows, `shutil.rmtree` does not handle read-only files very well. This handler
    makes sure the given file is writable, then re-execute the given removal function.

    Arguments:
        func: An OS-dependant function used to remove a file.
        path: The path to the file to remove.
        exc: An exception (Python >= 3.12) or `sys.exc_info()` object.
    """
    # TODO: Change to `excvalue = exc` when Python 3.11 support is dropped
    excvalue = cast(OSError, exc if isinstance(exc, BaseException) else exc[1])

    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        Path(path).chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


_re_whitespace = re.compile(r"^\s+|\s+$")


def normalize_git_path(path: str) -> str:
    r"""Convert weird characters returned by Git to normal UTF-8 path strings.

    A filename like âñ will be reported by Git as "\\303\\242\\303\\261" (octal notation).
    Similarly, a filename like "<tab>foo\b<lf>ar" will be reported as "\tfoo\\b\nar".
    This can be disabled with `git config core.quotepath off`.

    Args:
        path: The Git path to normalize.

    Returns:
        str: The normalized Git path.
    """
    # Remove surrounding quotes
    if path[0] == path[-1] == '"':
        path = path[1:-1]
    # Repair double-quotes
    path = path.replace('\\"', '"')
    # Unescape escape characters
    path = path.encode("latin-1", "backslashreplace").decode("unicode-escape")
    # Convert octal to utf8
    return path.encode("latin-1", "backslashreplace").decode("utf-8")


def escape_git_path(path: str) -> str:
    """Escape paths that will be used as literal gitwildmatch patterns.

    If the path was returned by a Git command, it should be unescaped completely.
    ``normalize_git_path`` can be used for this purpose.

    Args:
        path: The Git path to escape.

    Returns:
        str: The escaped Git path.
    """
    # GitWildMatchPattern.escape does not escape backslashes
    # or trailing whitespace.
    path = path.replace("\\", "\\\\")
    path = GitWildMatchPattern.escape(path)
    return _re_whitespace.sub(
        lambda match: "".join(f"\\{whitespace}" for whitespace in match.group()),
        path,
    )


def get_git_objects_dir(path: Path) -> Path:
    """Get the absolute path of a Git repository's objects directory."""
    # FIXME: A lazy import is currently necessary to avoid circular imports with
    # `errors.py`.
    from ._vcs import get_git

    git = get_git()
    return path.joinpath(
        git(
            "-C",
            path,
            "rev-parse",
            "--git-path",
            "objects",
        ).strip()
    ).absolute()


def set_git_alternates(*repos: Path, path: Path = Path()) -> None:
    """Set Git alternates to borrow Git objects from other repositories.

    Alternates are paths of other repositories' object directories written to
    `$GIT_DIR/objects/info/alternates` and delimited by the newline character.

    Args:
        *repos: The paths of repositories from which to borrow Git objects.
        path: The path of the repository where to set Git alternates. Defaults
            to the current working directory.
    """
    alternates_file = get_git_objects_dir(path) / "info" / "alternates"
    alternates_file.parent.mkdir(parents=True, exist_ok=True)
    alternates_file.write_bytes(b"\n".join(map(bytes, map(get_git_objects_dir, repos))))


def scantree(path: str, follow_symlinks: bool) -> Iterator[os.DirEntry[str]]:
    """A recursive extension of `os.scandir`."""
    for entry in os.scandir(path):
        yield entry
        if entry.is_dir(follow_symlinks=follow_symlinks):
            yield from scantree(entry.path, follow_symlinks)


_T = TypeVar("_T")
_E = TypeVar("_E", bound=Enum)


def try_enum(enum_type: type[_E], value: _T) -> _E | _T:
    """Try to convert a value into an enum.

    If the value is not a valid enum member, return the original value.
    """
    try:
        return enum_type(value)
    except ValueError:
        return value
