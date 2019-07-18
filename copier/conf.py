import datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
from hashlib import sha512
from os import urandom
from pydantic import BaseModel, validator

from .types import AnyByStrDict, CheckPathFunc, OptStrOrPathSeq, OptStrSeq, StrOrPath
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


# TODO: Does raising ValueError still makes sense?
def check_existing_dir(path) -> None:
    if not path.exists():
        raise ValueError("Project template not found")

    if not path.is_dir():
        raise ValueError("The project template must be a folder")


def resolve_path(path) -> Path:
    return Path(path).expanduser().resolve()


class Flags(BaseModel):
    pretend: bool = False
    quiet: bool = False
    force: bool = False
    skip: bool = False
    cleanup_on_error: bool = True

    # configuration
    class Config:
        allow_mutation = False


class ConfigData(BaseModel):
    src_path: Path
    dst_path: Path
    data: AnyByStrDict = DEFAULT_DATA
    extra_paths: Sequence[Path] = []
    exclude: OptStrOrPathSeq = DEFAULT_EXCLUDE
    include: OptStrOrPathSeq = ()
    skip_if_exists: OptStrOrPathSeq = None
    tasks: OptStrSeq = None
    envops: Optional[AnyByStrDict] = None

    # sanitizers
    @validator("src_path", "dst_path", "extra_paths", pre=True)
    def resolve_single_path(cls, v):
        return resolve_path(v)

    @validator("src_path", "extra_paths", pre=True)
    def ensure_dir_exist(cls, v):
        check_existing_dir(v)
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
) -> ConfigData:
    # https://stackoverflow.com/questions/10724495/getting-all-arguments-and-values-passed-to-a-function
    _locals = locals().copy()
    _locals = {k: v for k, v in _locals.items() if v is not None}

    file_data = load_config_data(src_path, quiet=True)
    config_data, query_data = filter_config(file_data)

    config_data["extra_paths"] = (
        config_data.get("extra_paths", None) or extra_paths or []
    )
    config_data["skip_if_exists"] = skip_if_exists or [
        p for p in config_data.get("_skip_if_exists", [])
    ]

    config_data = {k: v for k, v in config_data.items() if v is not None}

    if not force:
        query_data = query_user_data(query_data)

    config_data["data"] = {**DEFAULT_DATA.copy(), **query_data, **(data or {})}

    flags = Flags(
        pretend=pretend,
        quiet=quiet,
        force=force,
        skip=skip,
        cleanup_on_error=cleanup_on_error,
    )

    # flags = Flags(**_locals)  # TODO: Try this out.
    _locals.update(config_data)
    Path("_locals.log").write_text(str(_locals))
    return ConfigData(**_locals), flags
