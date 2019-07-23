import datetime
from typing import Tuple
from pathlib import Path
from hashlib import sha512
from os import urandom
from pydantic import BaseModel, validator, StrictBool, Extra

from ..types import AnyByStrDict, StrSeq, StrOrPathSeq, PathSeq


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
    pretend: StrictBool = False  # type: ignore
    quiet: StrictBool = False  # type: ignore
    force: StrictBool = False  # type: ignore
    skip: StrictBool = False  # type: ignore
    cleanup_on_error: StrictBool = True  # type: ignore

    class Config:
        allow_mutation = False


class EnvOps(BaseModel):
    autoescape: StrictBool = False  # type: ignore
    block_start_string: str = "[%"
    block_end_string: str = "%]"
    variable_start_string: str = "[["
    variable_end_string: str = "]]"
    keep_trailing_newline: StrictBool = True  # type: ignore

    class Config:
        allow_mutation = False
        extra = Extra.allow


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
    def resolve_path(cls, v: Path) -> Path:
        return Path(v).expanduser().resolve()

    @validator("src_path", "extra_paths", pre=True)
    def dir_must_exist(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError("Project template not found")
        if not v.is_dir():
            raise ValueError("The project template must be a folder")
        return v

    # configuration
    class Config:
        allow_mutation = False
        anystr_strip_whitespace = True
