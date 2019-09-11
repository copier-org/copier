import errno
import os
import shutil
import unicodedata
from fnmatch import fnmatch
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple, Union

import colorama
from colorama import Fore, Style
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

from .types import (
    AnyByStrDict,
    CheckPathFunc,
    IntSeq,
    OptStrOrPathSeq,
    StrOrPath,
    StrOrPathSeq,
    StrSeq,
    T,
)



_all__: Tuple[str, ...] = (
    "STYLE_OK",
    "STYLE_WARNING",
    "STYLE_IGNORE",
    "STYLE_DANGER",
    "printf",
    "prompt",
    "prompt_bool",
)

colorama.init()

STYLE_OK: IntSeq = [Fore.GREEN, Style.BRIGHT]
STYLE_WARNING: IntSeq = [Fore.YELLOW, Style.BRIGHT]
STYLE_IGNORE: IntSeq = [Fore.CYAN]
STYLE_DANGER: IntSeq = [Fore.RED, Style.BRIGHT]

INDENT = " " * 2
HLINE = "-" * 42

NO_VALUE: object = object()


def printf(
    action: str, msg: str = "", style: Optional[IntSeq] = None, indent: int = 10
) -> Optional[str]:
    action = action.rjust(indent, " ")
    if not style:
        return action + msg

    out = style + [action, Fore.RESET, Style.RESET_ALL, INDENT, msg]  # type: ignore
    print(*out, sep="")
    return None  # HACK: Satisfy MyPy


def printf_block(
    e: Exception,
    action: str,
    msg: str = "",
    style: IntSeq = STYLE_WARNING,
    indent: int = 0,
    quiet: bool = False,
) -> None:
    if not quiet:
        print("")
        printf(action, msg=msg, style=style, indent=indent)
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
    default: Optional[Union[bool, str, object]] = False,
    yes: str = "y",
    no: str = "n",
    yes_choices: Optional[StrSeq] = None,
    no_choices: Optional[StrSeq] = None,
) -> Optional[bool]:
    # TODO: Backwards compatibility. Remove for version 3.0
    if yes_choices:
        yes = yes_choices[0]
    if no_choices:
        no = no_choices[0]

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


def copy_file(src: Path, dst: Path, symlinks: bool = True) -> None:
    shutil.copy2(src, dst, follow_symlinks=symlinks)


class Renderer:
    def __init__(
        self, env: SandboxedEnvironment, src_path: Path, data: AnyByStrDict
    ) -> None:
        self.env = env
        self.src_path = src_path
        self.data = data

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
    return Renderer(env=env, src_path=src_path, data=data)


def normalize_str(text: StrOrPath, form: str = "NFD") -> str:
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, str(text))


def get_name_filters(
    exclude: StrOrPathSeq, include: StrOrPathSeq, skip_if_exists: StrOrPathSeq
) -> Tuple[CheckPathFunc, CheckPathFunc]:
    """Returns a function that evaluates if aCheckPathFunc file or folder name must be
    filtered out, and another that evaluates if a file must be skipped.

    The compared paths are first converted to unicode and decomposed.
    This is neccesary because the way PY2.* `os.walk` read unicode
    paths in different filesystems. For instance, in OSX, it returns a
    decomposed unicode string. In those systems, u'ñ' is read as `\u0303`
    instead of `\xf1`.
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
