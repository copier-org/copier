import errno
import os
import shutil
import unicodedata
from fnmatch import fnmatch
from functools import reduce
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import colorama  # type: ignore
import jinja2
from colorama import Fore, Style
from jinja2.sandbox import SandboxedEnvironment

from .types import OptSeqStrOrPath, AnyByStr, CheckPathFunc


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

STYLE_OK: List[int] = [Fore.GREEN, Style.BRIGHT]
STYLE_WARNING: List[int] = [Fore.YELLOW, Style.BRIGHT]
STYLE_IGNORE: List[int] = [Fore.CYAN]
STYLE_DANGER: List[int] = [Fore.RED, Style.BRIGHT]


def printf(
    action: str, msg: str = "", style: List[int] = None, indent: int = 10
) -> Optional[str]:
    action = action.rjust(indent, " ")
    if not style:
        return action + msg

    out = style + [action, Fore.RESET, Style.RESET_ALL, "  ", msg]  # type: ignore
    print(*out, sep="")
    return None  # HACK: Satisfy MyPy


def printf_block(
    e,
    action: str,
    msg: str = "",
    style: List[int] = STYLE_WARNING,
    indent: int = 0,
    quiet: bool = False,
):
    if not quiet:
        print("")
        printf(action, msg=msg, style=style, indent=indent)
        print("-" * 42)
        print(e)
        print("-" * 42)


no_value = object()


def required(value: object) -> object:
    if not value:
        raise ValueError()
    return value


def prompt(question, default=no_value, default_show=None, validator=required, **kwargs):
    """
    Prompt for a value from the command line. A default value can be provided,
    which will be used if no text is entered by the user. The value can be
    validated, and possibly changed by supplying a validator function. Any
    extra keyword arguments to this function will be passed along to the
    validator. If the validator raises a ValueError, the error message will be
    printed and the user asked to supply another value.
    """
    if default_show:
        question += " [{}] ".format(default_show)
    elif default and default is not no_value:
        question += " [{}] ".format(default)
    else:
        question += " "

    while True:
        resp = input(question)
        if not resp:
            if default is None:
                return None
            if default is not no_value:
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
    yes_choices: Optional[List[str]] = None,
    no_choices: Optional[List[str]] = None,
):
    # Backwards compatibility. Remove for version 3.0
    if yes_choices:
        yes = yes_choices[0]
    if no_choices:
        no = no_choices[0]

    please_answer = ' Please answer "{}" or "{}"'.format(yes, no)

    def validator(value):
        if value:
            value = str(value).lower()[0]
        if value == yes:
            return True
        elif value == no:
            return False
        else:
            raise ValueError(please_answer)

    if default is None:
        default = no_value
        default_show = yes + "/" + no
    elif default:
        default = yes
        default_show = yes.upper() + "/" + no
    else:
        default = no
        default_show = yes + "/" + no.upper()

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
    shutil.copy2(str(src), str(dst), follow_symlinks=symlinks)


# The default env options for jinja2
DEFAULT_ENV_OPTIONS: Dict[str, Union[bool, str, jinja2.FileSystemLoader]] = {
    "autoescape": False,
    "block_start_string": "[%",
    "block_end_string": "%]",
    "variable_start_string": "[[",
    "variable_end_string": "]]",
    "keep_trailing_newline": True,
}


class Renderer(object):
    def __init__(self, env, src_path, data):
        self.env = env
        self.src_path = src_path
        self.data = data

    def __call__(self, fullpath):
        relpath = str(fullpath).replace(self.src_path, "", 1).lstrip(os.path.sep)
        tmpl = self.env.get_template(relpath)
        return tmpl.render(**self.data)

    def string(self, string):
        tmpl = self.env.from_string(string)
        return tmpl.render(**self.data)


def get_jinja_renderer(
    src_path: Path,
    data: AnyByStr,
    extra_paths: OptSeqStrOrPath = None,
    envops: Optional[AnyByStr] = None,
) -> Renderer:
    """Returns a function that can render a Jinja template.
    """
    # Jinja <= 2.10 does not work with `pathlib.Path`s
    _src_path: str = str(src_path)
    _envops = DEFAULT_ENV_OPTIONS.copy()
    _envops.update(envops or {})

    paths = [_src_path] + [str(p) for p in extra_paths or []]
    _envops.setdefault("loader", jinja2.FileSystemLoader(paths))

    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(**_envops)
    return Renderer(env=env, src_path=_src_path, data=data)


def normalize_str(text: Union[str, Path], form: str = "NFD") -> str:
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, str(text))


def get_name_filters(
    exclude: Sequence[Union[str, Path]],
    include: Sequence[Union[str, Path]],
    skip_if_exists: Sequence[Union[str, Path]],
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

    def fullmatch(path: Union[str, Path], pattern: Union[str, Path]) -> bool:
        path = normalize_str(path)
        name = os.path.basename(path)
        return fnmatch(name, str(pattern)) or fnmatch(path, str(pattern))

    def match(path: Union[str, Path], patterns: Sequence[Union[str, Path]]) -> bool:
        return reduce(lambda r, pattern: r or fullmatch(path, pattern), patterns, False)

    def must_be_filtered(path: Union[str, Path]) -> bool:
        return match(path, exclude)

    def must_be_included(path: Union[str, Path]) -> bool:
        return match(path, include)

    def must_skip(path: Union[str, Path]) -> bool:
        return match(path, skip_if_exists)

    def must_filter(path: Union[str, Path]) -> bool:
        return must_be_filtered(path) and not must_be_included(path)

    return must_filter, must_skip
