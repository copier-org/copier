import datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
from hashlib import sha512
from os import urandom
from pydantic import BaseModel, validator

from .types import AnyByStrDict, CheckPathFunc, OptStrOrPathSeq, OptStrSeq, StrOrPath
from .user_data import load_config_data

# Default list of files in the template to exclude from the rendered project
DEFAULT_EXCLUDE = (
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

DEFAULT_INCLUDE = ()

DEFAULT_DATA = {
    "now": datetime.datetime.utcnow,
    "make_secret": lambda: sha512(urandom(48)).hexdigest(),
}

DEFAULT_FLAGS = {"pretend": False, "quiet": False, "force": False, "skip": False}

# TODO: Does raising ValueError still makes sense?
def check_existing_dir(path) -> None:
    if not path.exists():
        raise ValueError("Project template not found")

    if not path.is_dir():
        raise ValueError("The project template must be a folder")


# TODO: Does raising ValueError still makes sense?
# TODO: Rename to resolve_path
def resolve_path(path) -> Path:
    return Path(path).expanduser().resolve()
    # try:
    #     return Path(path).expanduser().resolve()
    # except FileNotFoundError:  # TODO: Is this ever raised?
    #     raise


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
    include: OptStrOrPathSeq = DEFAULT_INCLUDE
    skip_if_exists: OptStrOrPathSeq = None
    tasks: OptStrSeq = None
    envops: Optional[AnyByStrDict] = None
    flags: Dict = DEFAULT_FLAGS
    # new flags
    pretend: bool = False
    quiet: bool = False
    force: bool = False
    skip: bool = False
    cleanup_on_error: bool = True

    # sanitizers
    @validator("src_path", "dst_path", pre=True)
    def resolve_single_path(cls, v):
        return resolve_path(v)

    # @validator("extra_paths", pre=True)
    # def resolve_multiple_paths(cls, v):
    #     return [resolve_path(p) for p in v]

    # @validator("src_path", "extra_paths", pre=True)
    # def ensure_dir_exist(cls, v):
    #     # if isinstance(v, (list, set, tuple)):
    #     #     [check_existing_dir(p) for p in v or []]
    #     # check_existing_dir(v)
    #     return v

    # HACK
    @validator("dst_path", pre=True)
    def make_folder_name(cls, v):
        cls.folder_name = v.name  # TODO: Add folder_name to data?
        # cls.data["folder_name"] = v.name
        return v

    # configuration
    class Config:
        allow_mutation = False
        anystr_strip_whitespace = True


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

    _local_flags = {
        "pretend": pretend,
        "quiet": quiet,
        "force": force,
        "skip": skip,
        "cleanup_on_error": cleanup_on_error,
    }
    _default_flags = DEFAULT_FLAGS.copy()
    _default_flags.update(_local_flags)
    _locals["flags"] = _default_flags

    config_data = load_config_data(src_path, quiet=True)
    config_data["exclude"] = config_data.pop("_exclude", None)
    config_data["include"] = config_data.pop("_include", None)
    config_data["tasks"] = config_data.pop("_tasks", None)

    config_data["extra_paths"] = config_data.pop("_extra_paths", None) or extra_paths
    config_data["extra_paths"] = [
        resolve_path(p) for p in config_data["extra_paths"] or []
    ]

    config_data["skip_if_exists"] = skip_if_exists or [
        resolve_path(p) for p in config_data.pop("_skip_if_exists", [])
    ]
    # config_data["skip_if_exists"] = [resolve_path(p) for p in [skip_if_exists]]
    config_data = {k: v for k, v in config_data.items() if v is not None}

    # config_data = {k[1:]: v for k, v in config_data.items() if k.startswith("_")}
    _locals.update(config_data)

    Path("_locals.log").write_text(str(_locals))
    return ConfigData(**_locals)
    # try:
    #     return ConfigData(**_locals)
    # except Exception as e:
    #     Path("exception.log").write_text(str(e))
    #     Path("_locals.log").write_text(str(_locals))
