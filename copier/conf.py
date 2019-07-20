import datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
from hashlib import sha512
from os import urandom
from pydantic import BaseModel, validator

from .types import (
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

# Default list of files in the template to exclude from the rendered project
DEFAULT_EXCLUDE: Tuple[str, ...] = (
    "copier.yaml",
    "copier.yml",
    "copier.toml",
    "copier.json",
    "~*",
    "*.py[co]",
    "__pycache__",
    "__pycache__/*",
    ".git",
    ".git/*",
    ".DS_Store",
    ".svn",
)

DEFAULT_DATA: AnyByStrDict = {
    "now": datetime.datetime.utcnow,
    "make_secret": lambda: sha512(urandom(48)).hexdigest(),
}


class Flags(BaseModel):
    pretend: bool = False
    quiet: bool = False
    force: bool = False
    skip: bool = False
    cleanup_on_error: bool = True


class EnvOps(BaseModel):
    autoescape: bool = False
    block_start_string: str = "[%"
    block_end_string: str = "%]"
    variable_start_string: str = "[["
    variable_end_string: str = "]]"
    keep_trailing_newline: bool = True


class ConfigData(BaseModel):
    src_path: Path
    dst_path: Path
    data: AnyByStrDict = DEFAULT_DATA
    extra_paths: PathSeq = []
    exclude: StrOrPathSeq = DEFAULT_EXCLUDE
    include: StrOrPathSeq = []
    skip_if_exists: StrOrPathSeq = []
    tasks: StrSeq = []
    envops: EnvOps

    # sanitizers
    @validator("src_path", "dst_path", "extra_paths", pre=True)
    def resolve_single_path(cls, v):
        return Path(v).expanduser().resolve()

    @validator("src_path", "extra_paths", pre=True)
    def ensure_dir_exist(cls, v):
        if not v.exists():
            raise ValueError("Project template not found")
        if not v.is_dir():
            raise ValueError("The project template must be a folder")
        return v

    def __post_init_post_parse__(self):
        self.data["folder_name"] = self.src_path.name

    # configuration
    class Config:
        allow_mutation = False
        anystr_strip_whitespace = True


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
    pretend: bool = False,
    force: bool = False,
    skip: bool = False,
    quiet: bool = False,
    cleanup_on_error: bool = True,
    **kwargs
) -> Tuple[ConfigData, Flags]:
    # https://stackoverflow.com/questions/10724495/getting-all-arguments-and-values-passed-to-a-function
    _locals = locals().copy()
    _locals = {k: v for k, v in _locals.items() if v is not None}

    file_data = load_config_data(src_path, quiet=True)
    config_data, query_data = filter_config(file_data)

    if not force:
        query_data = query_user_data(query_data)

    # merge config sources in order of precedence
    config_data["data"] = {**DEFAULT_DATA.copy(), **query_data, **(data or {})}
    _locals = {**config_data, **_locals}
    _locals["envops"] = EnvOps(**_locals.get("envops", {}))

    return ConfigData(**_locals), Flags(**_locals)
