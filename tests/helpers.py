import filecmp
import os
import sys
import textwrap
from enum import Enum
from hashlib import sha1
from pathlib import Path
from typing import Dict

from prompt_toolkit.input.ansi_escape_sequences import REVERSE_ANSI_SEQUENCES
from prompt_toolkit.keys import Keys

import copier
from copier.types import StrOrPath

PROJECT_TEMPLATE = Path(__file__).parent / "demo"

DATA = {
    "py3": True,
    "make_secret": lambda: sha1(os.urandom(48)).hexdigest(),
    "myvar": "awesome",
    "what": "world",
    "project_name": "Copier",
    "version": "2.0.0",
    "description": "A library for rendering projects templates",
}


class Keyboard(str, Enum):
    ControlH = REVERSE_ANSI_SEQUENCES[Keys.ControlH]
    Enter = "\r"
    Esc = REVERSE_ANSI_SEQUENCES[Keys.Escape]

    # Equivalent keystrokes in terminals; see python-prompt-toolkit for
    # further explanations
    Alt = Esc
    Backspace = ControlH


def is_venv() -> bool:
    """Indicate if we are running inside a venv."""
    return sys.base_prefix != sys.prefix


def bin_prefix() -> str:
    """Obtain prefix for binaries inside the venv, if any."""
    if not is_venv():
        return ""
    return str(Path(sys.prefix, "bin"))


def render(tmp_path, **kwargs):
    kwargs.setdefault("quiet", True)
    copier.copy(str(PROJECT_TEMPLATE), tmp_path, data=DATA, **kwargs)


def assert_file(tmp_path, *path):
    p1 = os.path.join(str(tmp_path), *path)
    p2 = os.path.join(str(PROJECT_TEMPLATE), *path)
    assert filecmp.cmp(p1, p2)


def build_file_tree(spec: Dict[StrOrPath, str], dedent: bool = True):
    """Builds a file tree based on the received spec."""
    for path, contents in spec.items():
        path = Path(path)
        if dedent:
            contents = textwrap.dedent(contents)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fd:
            fd.write(contents)
