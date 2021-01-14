"""Pydantic models, exceptions and default values."""
import datetime
from hashlib import sha512
from os import urandom
from typing import Tuple

from pydantic import StrictBool
from pydantic.dataclasses import dataclass

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


class UserMessageError(Exception):
    """Exit the program giving a message to the user."""


class NoSrcPathError(UserMessageError):
    pass


@dataclass
class EnvOps:
    """Jinja2 environment options."""

    autoescape: StrictBool = False
    block_start_string: str = "[%"
    block_end_string: str = "%]"
    comment_start_string: str = "[#"
    comment_end_string: str = "#]"
    variable_start_string: str = "[["
    variable_end_string: str = "]]"
    keep_trailing_newline: StrictBool = True
