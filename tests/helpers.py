from __future__ import annotations

import filecmp
import json
import os
import sys
import textwrap
from collections.abc import Mapping
from enum import Enum
from hashlib import sha1
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pexpect.popen_spawn import PopenSpawn
from plumbum import local
from plumbum.cmd import git as _git
from plumbum.machines import LocalCommand
from prompt_toolkit.input.ansi_escape_sequences import REVERSE_ANSI_SEQUENCES
from prompt_toolkit.keys import Keys
from pytest_gitconfig.plugin import DEFAULT_GIT_USER_EMAIL, DEFAULT_GIT_USER_NAME

import copier
from copier._types import StrOrPath

if TYPE_CHECKING:
    from pexpect.spawnbase import SpawnBase

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
    # uv installs the executable as copier.cmd in Windows
    "copier.cmd",
    "copier",
)

# Executing copier this way allows to debug subprocesses using debugpy
# See https://github.com/microsoft/debugpy/issues/596#issuecomment-824643237
COPIER_PATH = (sys.executable, "-m", "copier")

# Helpers to use with tests designed for old copier bracket envops defaults
BRACKET_ENVOPS = {
    "autoescape": False,
    "block_end_string": "%]",
    "block_start_string": "[%",
    "comment_end_string": "#]",
    "comment_start_string": "[#",
    "keep_trailing_newline": True,
    "variable_end_string": "]]",
    "variable_start_string": "[[",
}
BRACKET_ENVOPS_JSON = json.dumps(BRACKET_ENVOPS)
SUFFIX_TMPL = ".tmpl"

COPIER_ANSWERS_FILE: Mapping[StrOrPath, str | bytes | Path] = {
    "{{ _copier_conf.answers_file }}.jinja": ("{{ _copier_answers|tojson }}")
}


class Spawn(Protocol):
    def __call__(
        self, cmd: tuple[str, ...], *, timeout: int | None = ...
    ) -> PopenSpawn: ...


class Keyboard(str, Enum):
    ControlH = REVERSE_ANSI_SEQUENCES[Keys.ControlH]
    ControlI = REVERSE_ANSI_SEQUENCES[Keys.ControlI]
    ControlC = REVERSE_ANSI_SEQUENCES[Keys.ControlC]
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
    Tab = ControlI


def render(tmp_path: Path, **kwargs: Any) -> None:
    kwargs.setdefault("quiet", True)
    copier.run_copy(str(PROJECT_TEMPLATE), tmp_path, data=DATA, **kwargs)


def assert_file(tmp_path: Path, *path: str) -> None:
    p1 = tmp_path.joinpath(*path)
    p2 = PROJECT_TEMPLATE.joinpath(*path)
    assert filecmp.cmp(p1, p2)


def build_file_tree(
    spec: Mapping[StrOrPath, str | bytes | Path],
    dedent: bool = True,
    encoding: str = "utf-8",
) -> None:
    """Builds a file tree based on the received spec.

    Params:
        spec:
            A mapping from filesystem paths to file contents. If the content is
            a Path object a symlink to the path will be created instead.

        dedent: Dedent file contents.
    """
    for path, contents in spec.items():
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, Path):
            os.symlink(str(contents), path)
        else:
            binary = isinstance(contents, bytes)
            if not binary and dedent:
                assert isinstance(contents, str)
                contents = textwrap.dedent(contents)
            mode = "wb" if binary else "w"
            enc = None if binary else encoding
            with Path(path).open(mode, encoding=enc) as fd:
                fd.write(contents)


def expect_prompt(
    tui: SpawnBase,
    name: str,
    expected_type: str,
    help: str | None = None,
) -> None:
    """Check that we get a prompt in the standard form"""
    if help:
        tui.expect_exact(help)
    else:
        tui.expect_exact(name)
        if expected_type != "str":
            tui.expect_exact(f"({expected_type})")


git: LocalCommand = _git.with_env(
    GIT_AUTHOR_NAME=DEFAULT_GIT_USER_NAME,
    GIT_AUTHOR_EMAIL=DEFAULT_GIT_USER_EMAIL,
    GIT_COMMITTER_NAME=DEFAULT_GIT_USER_NAME,
    GIT_COMMITTER_EMAIL=DEFAULT_GIT_USER_EMAIL,
)


def git_save(
    dst: StrOrPath = ".",
    message: str = "Test commit",
    tag: str | None = None,
    allow_empty: bool = False,
) -> None:
    """Save the current repo state in git.

    Args:
        dst: Path to the repo to save.
        message: Commit message.
        tag: Tag to create, optionally.
        allow_empty: Allow creating a commit with no changes
    """
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", message, *(["--allow-empty"] if allow_empty else []))
        if tag:
            git("tag", tag)


def git_init(message: str = "hello world") -> None:
    """Initialize a Git repository with a first commit.

    Args:
        message: The first commit message.
    """
    git("init")
    git("add", ".")
    git("commit", "-m", message)
