import filecmp
import os
import sys
import textwrap
from enum import Enum
from hashlib import sha1
from pathlib import Path
from typing import Dict

from plumbum import local
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

COPIER_CMD = local.get(
    # Allow debugging in VSCode
    # HACK https://github.com/microsoft/vscode-python/issues/14222
    str(Path(sys.executable).parent / "copier.cmd"),
    str(Path(sys.executable).parent / "copier"),
    # Poetry installs the executable as copier.cmd in Windows
    "copier.cmd",
    "copier",
)
COPIER_PATH = str(COPIER_CMD.executable)


class Keyboard(str, Enum):
    ControlH = REVERSE_ANSI_SEQUENCES[Keys.ControlH]
    Enter = "\r"
    Esc = REVERSE_ANSI_SEQUENCES[Keys.Escape]

    Home = REVERSE_ANSI_SEQUENCES[Keys.Home]
    End = REVERSE_ANSI_SEQUENCES[Keys.End]

    Up = REVERSE_ANSI_SEQUENCES[Keys.Up]
    Down = REVERSE_ANSI_SEQUENCES[Keys.Down]
    Right = REVERSE_ANSI_SEQUENCES[Keys.Right]
    Left = REVERSE_ANSI_SEQUENCES[Keys.Left]

    # Equivalent keystrokes in terminals; see python-prompt-toolkit for
    # further explanations
    Alt = Esc
    Backspace = ControlH


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
