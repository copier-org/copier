import datetime
from hashlib import sha512
from os import urandom
from pathlib import Path
from typing import Any, Sequence, Tuple

from pydantic import BaseModel, Extra, StrictBool, validator

from ..types import AnyByStrDict, OptStr, PathSeq, StrOrPathSeq, StrSeq

# Default list of files in the template to exclude from the rendered project
DEFAULT_EXCLUDE: Tuple[str, ...] = (
    "copier.yaml",
    "copier.yml",
    "~*",
    "*.py[co]",
    "__pycache__",
    ".git",
    ".DS_Store",
    ".svn",
)

DEFAULT_DATA: AnyByStrDict = {
    "now": datetime.datetime.utcnow,
    "make_secret": lambda: sha512(urandom(48)).hexdigest(),
}

DEFAULT_TEMPLATES_SUFFIX = ".tmpl"


class UserMessageError(Exception):
    """Exit the program giving a message to the user."""

    pass


class NoSrcPathError(UserMessageError):
    pass


class EnvOps(BaseModel):
    autoescape: StrictBool = False
    block_start_string: str = "[%"
    block_end_string: str = "%]"
    comment_start_string: str = "[#"
    comment_end_string: str = "#]"
    variable_start_string: str = "[["
    variable_end_string: str = "]]"
    keep_trailing_newline: StrictBool = True

    class Config:
        allow_mutation = False
        extra = Extra.allow


class Migrations(BaseModel):
    version: str
    before: StrSeq = ()
    after: StrSeq = ()


class ConfigData(BaseModel):
    src_path: Path
    dst_path: Path
    data: AnyByStrDict = {}
    extra_paths: PathSeq = ()
    exclude: StrOrPathSeq = DEFAULT_EXCLUDE
    skip_if_exists: StrOrPathSeq = ()
    tasks: StrSeq = ()
    envops: EnvOps = EnvOps()
    templates_suffix: str = DEFAULT_TEMPLATES_SUFFIX
    original_src_path: OptStr
    commit: OptStr
    old_commit: OptStr
    cleanup_on_error: StrictBool = True
    force: StrictBool = False
    only_diff: StrictBool = True
    pretend: StrictBool = False
    quiet: StrictBool = False
    skip: StrictBool = False
    vcs_ref: OptStr
    migrations: Sequence[Migrations] = ()

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.data.update(dict(DEFAULT_DATA, _folder_name=self.dst_path.name))

    @validator("skip", always=True)
    def mutually_exclusive_flags(cls, v, values):  # noqa: B902
        if v and values["force"]:
            raise ValueError(f"Flags `force` and `skip` are mutually exclusive.")
        return v

    # sanitizers
    @validator("src_path", "dst_path", "extra_paths", pre=True, each_item=True)
    def resolve_path(cls, v: Path) -> Path:  # noqa: B902
        return Path(v).expanduser().resolve()

    @validator("src_path", "extra_paths", pre=True, each_item=True)
    def dir_must_exist(cls, v: Path) -> Path:  # noqa: B902
        if not v.exists():
            raise ValueError("Project template not found.")
        if not v.is_dir():
            raise ValueError("Project template not a folder.")
        return v

    # configuration
    class Config:
        allow_mutation = False
        anystr_strip_whitespace = True
