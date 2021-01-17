"""Pydantic models, exceptions and default values."""
import datetime
from hashlib import sha512
from os import urandom
from pathlib import Path
from typing import Tuple

from pydantic.main import BaseModel

from ..types import AnyByStrDict

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


# TODO Delete
class ConfigData(BaseModel):
    """A model holding configuration data."""

    src_path: Path
    dst_path: Path
    answers_file: Path = Path(".copier-answers.yml")
