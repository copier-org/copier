"""Some utility functions."""

import errno
import os
import platform
import stat
import sys
from contextlib import suppress
from importlib.metadata import version
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Literal, Optional, TextIO, Tuple, Union, cast

import colorama
from packaging.version import Version
from pydantic import StrictBool

from .types import IntSeq

colorama.init()


class Style:
    """Common color styles."""

    OK: IntSeq = [colorama.Fore.GREEN, colorama.Style.BRIGHT]
    WARNING: IntSeq = [colorama.Fore.YELLOW, colorama.Style.BRIGHT]
    IGNORE: IntSeq = [colorama.Fore.CYAN]
    DANGER: IntSeq = [colorama.Fore.RED, colorama.Style.BRIGHT]
    RESET: IntSeq = [colorama.Fore.RESET, colorama.Style.RESET_ALL]


INDENT = " " * 2
HLINE = "-" * 42

OS: Optional[Literal["linux", "macos", "windows"]] = cast(
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
    style: Optional[IntSeq] = None,
    indent: int = 10,
    quiet: Union[bool, StrictBool] = False,
    file_: TextIO = sys.stdout,
) -> Optional[str]:
    """Print string with common format."""
    if quiet:
        return None  # HACK: Satisfy MyPy
    _msg = str(msg)
    action = action.rjust(indent, " ")
    if not style:
        return action + _msg

    out = style + [action] + Style.RESET + [INDENT, _msg]  # type: ignore
    print(*out, sep="", file=file_)
    return None  # HACK: Satisfy MyPy


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


def cast_str_to_bool(value: Any) -> bool:
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
    func: Callable, path: str, exc: Tuple[BaseException, OSError, TracebackType]
) -> None:
    """Handle errors when trying to remove read-only files through `shutil.rmtree`.

    On Windows, `shutil.rmtree` does not handle read-only files very well. This handler
    makes sure the given file is writable, then re-execute the given removal function.

    Arguments:
        func: An OS-dependant function used to remove a file.
        path: The path to the file to remove.
        exc: A `sys.exc_info()` object.
    """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


def readlink(link: Path) -> Path:
    """A custom version of os.readlink/pathlib.Path.readlink.

    pathlib.Path.readlink is what we ideally would want to use, but it is only available on python>=3.9.
    """
    if sys.version_info >= (3, 9):
        return link.readlink()
    else:
        return Path(os.readlink(link))
