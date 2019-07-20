import datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
from hashlib import sha512
from os import urandom
from pydantic import BaseModel, validator

from .objects import ConfigData, DEFAULT_DATA, Flags, EnvOps
from ..types import (
    AnyByStrDict,
    CheckPathFunc,
    OptStrOrPathSeq,
    StrSeq,
    OptStrSeq,
    StrOrPath,
    StrOrPathSeq,
    PathSeq,
)
from .user_data import load_config_data, query_user_data

__all__ = "make_config"


def filter_config(data: AnyByStrDict) -> Tuple[AnyByStrDict, AnyByStrDict]:
    """Separates config and query data."""
    conf_data = {}
    query_data = {}
    for k, v in data.items():
        if k.startswith("_"):
            conf_data[k[1:]] = v
        else:
            query_data[k] = v
    return conf_data, query_data


def make_config(
    src_path: str,
    dst_path: str,
    data: AnyByStrDict = None,
    *,
    exclude: OptStrSeq = None,
    include: OptStrSeq = None,
    skip_if_exists: OptStrSeq = None,
    tasks: OptStrSeq = None,
    envops: AnyByStrDict = None,
    extra_paths: OptStrSeq = None,
    pretend: Optional[bool] = False,
    force: Optional[bool] = False,
    skip: Optional[bool] = False,
    quiet: Optional[bool] = False,
    cleanup_on_error: Optional[bool] = True,
    **kwargs
) -> Tuple[ConfigData, Flags]:
    _locals = {k: v for k, v in locals().items() if v is not None}

    file_data = load_config_data(src_path, quiet=True)
    config_data, query_data = filter_config(file_data)

    if not force:
        query_data = query_user_data(query_data)

    # merge config sources in order of precedence
    config_data["data"] = {**DEFAULT_DATA.copy(), **query_data, **(data or {})}
    _locals = {**config_data, **_locals}
    _locals["envops"] = EnvOps(**_locals.get("envops", {}))

    return ConfigData(**_locals), Flags(**_locals)
