"""Jinja2 extensions."""

from __future__ import annotations

import re
import uuid
from base64 import b64decode, b64encode
from collections.abc import Iterator
from datetime import datetime
from functools import reduce
from hashlib import new as new_hash
from json import dumps as to_json, loads as from_json
from ntpath import (
    basename as win_basename,
    dirname as win_dirname,
    splitdrive as win_splitdrive,
)
from os.path import expanduser, expandvars, realpath, relpath, splitext
from pathlib import Path
from posixpath import basename, dirname
from random import Random
from shlex import quote
from time import gmtime, localtime, strftime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    Literal,
    Sequence,
    TypeVar,
    overload,
)
from warnings import warn

import yaml
from jinja2 import Environment, Undefined, UndefinedError, pass_environment
from jinja2.ext import Extension
from jinja2.filters import do_groupby

from .tools import cast_to_bool

if TYPE_CHECKING:
    from typing_extensions import TypeGuard

_T = TypeVar("_T")

_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "https://github.com/copier-org/copier")


def _is_sequence(obj: object) -> TypeGuard[Sequence[Any]]:
    return hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes))


def _do_b64decode(value: str) -> str:
    return b64decode(value).decode()


def _do_b64encode(value: str) -> str:
    return b64encode(value.encode()).decode()


def _do_bool(value: Any) -> bool | None:
    return None if value is None else cast_to_bool(value)


def _do_hash(value: str, algorithm: str) -> str:
    hasher = new_hash(algorithm)
    hasher.update(value.encode())
    return hasher.hexdigest()


def _do_sha1(value: str) -> str:
    return _do_hash(value, "sha1")


def _do_md5(value: str) -> str:
    return _do_hash(value, "md5")


def _do_mandatory(value: _T, msg: str | None = None) -> _T:
    if isinstance(value, Undefined):
        # See https://jinja.palletsprojects.com/en/3.1.x/api/#jinja2.Undefined._undefined_name
        raise UndefinedError(
            msg
            or f'Mandatory variable `{value._undefined_name or "<unknown>"}` is undefined'
        )
    return value


def _do_to_uuid(name: str, namespace: str | uuid.UUID = _UUID_NAMESPACE) -> str:
    if not isinstance(namespace, uuid.UUID):
        namespace = uuid.UUID(namespace)
    return str(uuid.uuid5(namespace, name))


def _do_to_yaml(value: Any, *args: Any, **kwargs: Any) -> str:
    kwargs.setdefault("allow_unicode", True)
    return yaml.dump(value, *args, **kwargs)  # type: ignore[no-any-return]


def _do_from_yaml(value: str) -> Any:
    return yaml.load(value, Loader=yaml.SafeLoader)


def _do_from_yaml_all(value: str) -> Iterator[Any]:
    return yaml.load_all(value, Loader=yaml.SafeLoader)


def _do_strftime(format: str, seconds: float | None = None, utc: bool = False) -> str:
    return strftime(format, gmtime(seconds) if utc else localtime(seconds))


def _do_to_datetime(date_string: str, format: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(date_string, format)


def _do_ternary(condition: bool | None, true: Any, false: Any, none: Any = None) -> Any:
    if condition is None:
        return none
    return true if condition else false


def _do_to_nice_json(value: Any, /, **kwargs: Any) -> str:
    kwargs.setdefault("skipkeys", False)
    kwargs.setdefault("ensure_ascii", True)
    kwargs.setdefault("check_circular", True)
    kwargs.setdefault("allow_nan", True)
    kwargs.setdefault("indent", 4)
    kwargs.setdefault("sort_keys", True)
    return to_json(value, **kwargs)


def _do_to_nice_yaml(value: Any, *args: Any, **kwargs: Any) -> str:
    kwargs.setdefault("allow_unicode", True)
    kwargs.setdefault("indent", 4)
    return yaml.dump(value, *args, **kwargs)  # type: ignore[no-any-return]


def _do_shuffle(seq: Sequence[_T], seed: str | None = None) -> list[_T]:
    seq = list(seq)
    Random(seed).shuffle(seq)
    return seq


@overload
def _do_random(stop: int, start: int, step: int, seed: str | None) -> int: ...


@overload
def _do_random(stop: Sequence[_T], start: None, step: None, seed: str | None) -> _T: ...


def _do_random(
    stop: int | Sequence[_T],
    start: int | None = None,
    step: int | None = None,
    seed: str | None = None,
) -> int | _T:
    rng = Random(seed)

    if isinstance(stop, int):
        if start is None:
            start = 0
        if step is None:
            step = 1
        return rng.randrange(start, stop, step)

    for arg_name, arg_value in [("start", start), ("stop", stop)]:
        if arg_value is None:
            raise TypeError(f'"{arg_name}" can only be used when "stop" is an integer')
    return rng.choice(stop)


def _do_flatten(
    seq: Sequence[Any], levels: int | None = None, skip_nulls: bool = True
) -> Sequence[Any]:
    if levels is not None:
        if levels < 1:
            return seq
        levels -= 1
    result: list[Any] = []
    for item in seq:
        if _is_sequence(item):
            result.extend(_do_flatten(item, levels, skip_nulls))
        elif not skip_nulls or item is not None:
            result.append(item)
    return result


def _do_fileglob(pattern: str) -> Sequence[str]:
    return [str(path) for path in Path(".").glob(pattern) if path.is_file()]


def _do_random_mac(prefix: str, seed: str | None = None) -> str:
    parts = prefix.lower().strip(":").split(":")
    if len(parts) > 5:
        raise ValueError(f"Invalid MAC address prefix {prefix}: too many parts")
    for part in parts:
        if not re.match(r"[a-f0-9]{2}", part):
            raise ValueError(
                f"Invalid MAC address prefix {prefix}: {part} is not a hexadecimal byte"
            )
    rng = Random(seed)
    return ":".join(
        parts + [f"{rng.randint(0, 255):02x}" for _ in range(6 - len(parts))]
    )


def _do_regex_escape(
    pattern: str, re_type: Literal["python", "posix_basic"] = "python"
) -> str:
    if re_type == "python":
        return re.escape(pattern)
    raise NotImplementedError(f"Regex type {re_type} not implemented")


def _do_regex_search(
    value: str,
    pattern: str,
    *args: str,
    ignorecase: bool = False,
    multiline: bool = False,
) -> str | list[str] | None:
    groups: list[str | int] = []
    for arg in args:
        if match := re.match(r"^\\g<(\S+)>$", arg):
            groups.append(match.group(1))
        elif match := re.match(r"^\\(\d+)$", arg):
            groups.append(int(match.group(1)))
        else:
            raise ValueError("Invalid backref format")

    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE

    return (match := re.search(pattern, value, flags)) and (
        list(result) if isinstance((result := match.group(*groups)), tuple) else result
    )


def _do_regex_replace(
    value: str,
    pattern: str,
    replacement: str,
    *,
    ignorecase: bool = False,
) -> str:
    return re.sub(pattern, replacement, value, flags=re.I if ignorecase else 0)


def _do_regex_findall(
    value: str,
    pattern: str,
    *,
    ignorecase: bool = False,
    multiline: bool = False,
) -> list[str]:
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    return re.findall(pattern, value, flags)


def _do_type_debug(value: object) -> str:
    return value.__class__.__name__


@pass_environment
def _do_extract(
    environment: Environment,
    key: Any,
    container: Any,
    *,
    morekeys: Any | Sequence[Any] | None = None,
) -> Any | Undefined:
    keys: list[Any]
    if morekeys is None:
        keys = [key]
    elif _is_sequence(morekeys):
        keys = [key, *morekeys]
    else:
        keys = [key, morekeys]
    return reduce(environment.getitem, keys, container)


class CopierExtension(Extension):
    """Jinja2 extension for Copier."""

    # NOTE: mypy disallows `Callable[[Any, ...], Any]`
    _filters: Final[dict[str, Callable[..., Any]]] = {
        "ans_groupby": do_groupby,
        "ans_random": _do_random,
        "b64decode": _do_b64decode,
        "b64encode": _do_b64encode,
        "basename": basename,
        "bool": _do_bool,
        "checksum": _do_sha1,
        "dirname": dirname,
        "expanduser": expanduser,
        "expandvars": expandvars,
        "extract": _do_extract,
        "fileglob": _do_fileglob,
        "flatten": _do_flatten,
        "from_json": from_json,
        "from_yaml": _do_from_yaml,
        "from_yaml_all": _do_from_yaml_all,
        "hash": _do_hash,
        "mandatory": _do_mandatory,
        "md5": _do_md5,
        "quote": quote,
        "random_mac": _do_random_mac,
        "realpath": realpath,
        "regex_escape": _do_regex_escape,
        "regex_findall": _do_regex_findall,
        "regex_replace": _do_regex_replace,
        "regex_search": _do_regex_search,
        "relpath": relpath,
        "sha1": _do_sha1,
        "shuffle": _do_shuffle,
        "splitext": splitext,
        "strftime": _do_strftime,
        "ternary": _do_ternary,
        "to_datetime": _do_to_datetime,
        "to_json": to_json,
        "to_nice_json": _do_to_nice_json,
        "to_nice_yaml": _do_to_nice_yaml,
        "to_uuid": _do_to_uuid,
        "to_yaml": _do_to_yaml,
        "type_debug": _do_type_debug,
        "win_basename": win_basename,
        "win_dirname": win_dirname,
        "win_splitdrive": win_splitdrive,
    }

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        for k, v in self._filters.items():
            if k in environment.filters:
                warn(
                    f'A filter named "{k}" already exists in the Jinja2 environment',
                    category=RuntimeWarning,
                    stacklevel=2,
                )
            else:
                environment.filters[k] = v
