import errno
import os
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import colorama
import pathspec
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from packaging import version
from pydantic import StrictBool
from yaml import safe_dump

from .config.objects import ConfigData, EnvOps
from .types import (
    AnyByStrDict,
    CheckPathFunc,
    Filters,
    IntSeq,
    JSONSerializable,
    LoaderPaths,
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
    result = safe_dump(data, **kwargs)
    if isinstance(result, str):
        result = result.rstrip()
    return result or ""


def get_jinja_env(
    envops: EnvOps,
    filters: Optional[Filters] = None,
    paths: Optional[LoaderPaths] = None,
    **kwargs: Any,
) -> SandboxedEnvironment:
    """Return a pre-configured Jinja environment."""
    loader = FileSystemLoader(paths) if paths else None
    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(loader=loader, **envops.dict(), **kwargs)
    default_filters = {"to_nice_yaml": to_nice_yaml}
    default_filters.update(filters or {})
    env.filters.update(default_filters)
    return env


class Renderer:
    def __init__(self, conf: ConfigData) -> None:
        envops: EnvOps = conf.envops
        paths = [str(conf.src_path)] + list(map(str, conf.extra_paths or []))
        self.env = get_jinja_env(envops=envops, paths=paths)
        self.conf = conf
        answers: AnyByStrDict = {}
        # All internal values must appear first
        if conf.commit:
            answers["_commit"] = conf.commit
        if conf.original_src_path is not None:
            answers["_src_path"] = conf.original_src_path
        # Other data goes next
        answers.update(
            (k, v)
            for (k, v) in conf.data.items()
            if not k.startswith("_")
            and k not in conf.secret_questions
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        )
        self.data = dict(
            conf.data,
            _copier_answers=answers,
            _copier_conf=conf.copy(deep=True, exclude={"data": {"now", "make_secret"}}),
        )

    def __call__(self, fullpath: StrOrPath) -> str:
        relpath = (
            str(fullpath).replace(str(self.conf.src_path), "", 1).lstrip(os.path.sep)
        )
        tmpl = self.env.get_template(relpath)
        return tmpl.render(**self.data)

    def string(self, string: StrOrPath) -> str:
        tmpl = self.env.from_string(str(string))
        return tmpl.render(**self.data)


def normalize_str(text: StrOrPath, form: str = "NFD") -> str:
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, str(text))


def create_path_filter(patterns: StrOrPathSeq) -> CheckPathFunc:
    """Returns a function that matches a path against given patterns."""
    patterns = [normalize_str(p) for p in patterns]
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def match(path: StrOrPath) -> bool:
        return spec.match_file(str(path))

    return match


def get_migration_tasks(conf: ConfigData, stage: str) -> List[Dict]:
    """Get migration objects that match current version spec.

    Versions are compared using PEP 440.
    """
    result: List[Dict] = []
    if not conf.old_commit or not conf.commit:
        return result
    vfrom = version.parse(conf.old_commit)
    vto = version.parse(conf.commit)
    extra_env = {
        "STAGE": stage,
        "VERSION_FROM": conf.old_commit,
        "VERSION_TO": conf.commit,
    }
    for migration in conf.migrations:
        if vto >= version.parse(migration.version) > vfrom:
            extra_env = dict(extra_env, VERSION_CURRENT=str(migration.version))
            result += [
                {"task": task, "extra_env": extra_env}
                for task in migration.dict().get(stage, [])
            ]
    return result
