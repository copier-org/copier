import errno
import os
import shutil
import unicodedata
from fnmatch import fnmatch
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple, Union

import colorama
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from pydantic import StrictBool
from ruamel.yaml import round_trip_dump

from .types import (
    AnyByStrDict,
    CheckPathFunc,
    IntSeq,
    JSONSerializable,
    OptStrOrPathSeq,
    OptBool,
    OptStr,
    StrOrPath,
    StrOrPathSeq,
    T,
)
from .version import __version__

__all__ = (
    "Style",
    "printf",
    "prompt",
    "prompt_bool",
)

colorama.init()


class Style:
    OK: IntSeq = [colorama.Fore.GREEN, colorama.Style.BRIGHT]
    WARNING: IntSeq = [colorama.Fore.YELLOW, colorama.Style.BRIGHT]
    IGNORE: IntSeq = [colorama.Fore.CYAN]
    DANGER: IntSeq = [colorama.Fore.RED, colorama.Style.BRIGHT]
    RESET: IntSeq = [colorama.Fore.RESET, colorama.Style.RESET_ALL]


INDENT = " " * 2
HLINE = "-" * 42

NO_VALUE: object = object()


def printf(
    action: str,
    msg: Any = "",
    style: Optional[IntSeq] = None,
    indent: int = 10,
    quiet: Union[bool, StrictBool] = False,
) -> Optional[str]:
    if quiet:
        return None  # HACK: Satisfy MyPy
    _msg = str(msg)
    action = action.rjust(indent, " ")
    if not style:
        return action + _msg

    out = style + [action] + Style.RESET + [INDENT, _msg]  # type: ignore
    print(*out, sep="")
    return None  # HACK: Satisfy MyPy


def printf_exception(
    e: Exception,
    action: str,
    msg: str = "",
    indent: int = 0,
    quiet: bool = False,
) -> None:
    if not quiet:
        print("")
        printf(action, msg=msg, style=Style.DANGER, indent=indent)
        print(HLINE)
        print(e)
        print(HLINE)


def required(value: T, **kwargs: Any) -> T:
    if not value:
        raise ValueError()
    return value


def prompt(
    question: str,
    default: Optional[Any] = NO_VALUE,
    default_show: Optional[Any] = None,
    validator: Callable = required,
    **kwargs: AnyByStrDict,
) -> Optional[Any]:
    """
    Prompt for a value from the command line. A default value can be provided,
    which will be used if no text is entered by the user. The value can be
    validated, and possibly changed by supplying a validator function. Any
    extra keyword arguments to this function will be passed along to the
    validator. If the validator raises a ValueError, the error message will be
    printed and the user asked to supply another value.
    """
    if default_show:
        question += f" [{default_show}] "
    elif default and default is not NO_VALUE:
        question += f" [{default}] "
    else:
        question += " "

    while True:
        resp = input(question)
        if not resp:
            if default is None:
                return None
            if default is not NO_VALUE:
                resp = default

        try:
            return validator(resp, **kwargs)
        except ValueError as e:
            if str(e):
                print(str(e))


def prompt_bool(
    question: str,
    default: Optional[Any] = False,
    yes: str = "y",
    no: str = "n",
) -> OptBool:
    please_answer = f' Please answer "{yes}" or "{no}"'

    def validator(value: Union[str, bool], **kwargs) -> Union[str, bool]:
        if value:
            value = str(value).lower()[0]
        if value == yes:
            return True
        elif value == no:
            return False
        else:
            raise ValueError(please_answer)

    if default is None:
        default = NO_VALUE
        default_show = f"{yes}/{no}"
    elif default:
        default = yes
        default_show = f"{yes.upper()}/{no}"
    else:
        default = no
        default_show = f"{yes}/{no.upper()}"

    return prompt(
        question, default=default, default_show=default_show, validator=validator
    )


def make_folder(folder: Path) -> None:
    if not folder.exists():
        try:
            os.makedirs(str(folder))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


def copy_file(src_path: Path, dst_path: Path, follow_symlinks: bool = True) -> None:
    shutil.copy2(src_path, dst_path, follow_symlinks=follow_symlinks)


def to_nice_yaml(data: Any, **kwargs) -> Optional[str]:
    """Dump a string to pretty YAML."""
    # Remove security-problematic kwargs
    kwargs.pop("stream", None)
    kwargs.pop("Dumper", None)
    result = round_trip_dump(data, **kwargs)
    if isinstance(result, str):
        result = result.rstrip()
    return result


class Renderer:
    def __init__(
        self, env: SandboxedEnvironment, src_path: Path, data: AnyByStrDict,
        original_src_path: OptStr,
    ) -> None:
        self.env = env
        self.src_path = src_path
        log: AnyByStrDict = {}
        # All internal values must appear first
        if original_src_path is not None:
            log["_src_path"] = original_src_path
        # Other data goes next
        log.update(
            (k, v) for (k, v) in data.items()
            if isinstance(k, JSONSerializable) and isinstance(v, JSONSerializable)
        )
        self.data = dict(data, _log=log)
        self.env.filters["to_nice_yaml"] = to_nice_yaml

    def __call__(self, fullpath: StrOrPath) -> str:
        relpath = str(fullpath).replace(str(self.src_path), "", 1).lstrip(os.path.sep)
        tmpl = self.env.get_template(relpath)
        return tmpl.render(**self.data)

    def string(self, string: StrOrPath) -> str:
        tmpl = self.env.from_string(str(string))
        return tmpl.render(**self.data)


def get_jinja_renderer(
    src_path: Path,
    data: AnyByStrDict,
    extra_paths: OptStrOrPathSeq = None,
    envops: Optional[AnyByStrDict] = None,
    original_src_path: OptStr = None,
) -> Renderer:
    """Returns a function that can render a Jinja template.
    """
    envops = envops or {}

    paths = [src_path] + [Path(p) for p in extra_paths or []]
    envops.setdefault("loader", FileSystemLoader(paths))  # type: ignore

    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(**envops)
    return Renderer(env=env, src_path=src_path, data=data,
                    original_src_path=original_src_path)


def normalize_str(text: StrOrPath, form: str = "NFD") -> str:
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, str(text))


def get_name_filters(
    exclude: StrOrPathSeq, include: StrOrPathSeq, skip_if_exists: StrOrPathSeq
) -> Tuple[CheckPathFunc, CheckPathFunc]:
    """Returns a function that evaluates if aCheckPathFunc file or folder name must be
    filtered out, and another that evaluates if a file must be skipped.
    """
    exclude = [normalize_str(pattern) for pattern in exclude]
    include = [normalize_str(pattern) for pattern in include]
    skip_if_exists = [normalize_str(pattern) for pattern in skip_if_exists]

    def fullmatch(path: StrOrPath, pattern: StrOrPath) -> bool:
        path = normalize_str(path)
        name = os.path.basename(path)
        return fnmatch(name, str(pattern)) or fnmatch(path, str(pattern))

    def match(path: StrOrPath, patterns: Sequence[StrOrPath]) -> bool:
        return reduce(lambda r, pattern: r or fullmatch(path, pattern), patterns, False)

    def must_be_filtered(path: StrOrPath) -> bool:
        return match(path, exclude)

    def must_be_included(path: StrOrPath) -> bool:
        return match(path, include)

    def must_skip(path: StrOrPath) -> bool:
        return match(path, skip_if_exists)

    def must_filter(path: StrOrPath) -> bool:
        return must_be_filtered(path) and not must_be_included(path)

    return must_filter, must_skip
