import errno
import os
import shutil
import unicodedata
from fnmatch import fnmatch
from functools import reduce
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple, Union

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
    OptStr,
    OptStrOrPathSeq,
    StrOrPath,
    StrOrPathSeq,
    T,
)

__all__ = ("Style", "printf")

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
    e: Exception, action: str, msg: str = "", indent: int = 0, quiet: bool = False
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


def make_folder(folder: Path) -> None:
    if not folder.exists():
        try:
            os.makedirs(str(folder))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


def copy_file(src_path: Path, dst_path: Path, follow_symlinks: bool = True) -> None:
    shutil.copy2(src_path, dst_path, follow_symlinks=follow_symlinks)


def to_nice_yaml(data: Any, **kwargs) -> str:
    """Dump a string to pretty YAML."""
    # Remove security-problematic kwargs
    kwargs.pop("stream", None)
    kwargs.pop("Dumper", None)
    result = round_trip_dump(data, **kwargs)
    if isinstance(result, str):
        result = result.rstrip()
    return result or ""


class Renderer:
    def __init__(
        self,
        env: SandboxedEnvironment,
        src_path: Path,
        data: AnyByStrDict,
        original_src_path: OptStr,
        commit: OptStr,
    ) -> None:
        self.env = env
        self.src_path = src_path
        answers: AnyByStrDict = {}
        # All internal values must appear first
        if commit:
            answers["_commit"] = commit
        if original_src_path is not None:
            answers["_src_path"] = original_src_path
        # Other data goes next
        answers.update(
            (k, v)
            for (k, v) in sorted(data.items())
            if not k.startswith("_")
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )
        self.data = dict(data, _copier_answers=answers)
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
    commit: OptStr = None,
) -> Renderer:
    """Returns a function that can render a Jinja template.
    """
    envops = envops or {}

    paths = [str(src_path)] + list(map(str, extra_paths or []))

    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(loader=FileSystemLoader(paths), **envops)
    return Renderer(
        env=env,
        src_path=src_path,
        data=data,
        original_src_path=original_src_path,
        commit=commit,
    )


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
