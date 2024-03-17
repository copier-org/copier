from __future__ import annotations

import platform
import sys
from typing import Iterator

import pytest
from coverage.tracer import CTracer
from pexpect.popen_spawn import PopenSpawn
from plumbum import local
from pytest_gitconfig.plugin import GitConfig

from .helpers import Spawn


@pytest.fixture
def spawn() -> Spawn:
    """Spawn a copier process TUI to interact with."""
    if platform.system() == "Windows":
        # HACK https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1243#issuecomment-706668723
        # FIXME Use pexpect or wexpect somehow to fix this
        pytest.xfail(
            "pexpect fails on Windows",
        )

    def _spawn(cmd: tuple[str, ...], *, timeout: int | None = None) -> PopenSpawn:
        # Disable subprocess timeout if debugging (except coverage), for commodity
        # See https://stackoverflow.com/a/67065084/1468388
        tracer = getattr(sys, "gettrace", lambda: None)()
        if not isinstance(tracer, (CTracer, type(None))):
            timeout = None
        # Using PopenSpawn, although probably it would be best to use pexpect.spawn
        # instead. However, it's working fine and it seems easier to fix in the
        # future to work on Windows (where, this way, spawning actually works; it's just
        # python-prompt-toolkit that rejects displaying a TUI)
        return PopenSpawn(cmd, timeout, logfile=sys.stderr.buffer)

    return _spawn


@pytest.fixture(scope="session", autouse=True)
def default_gitconfig(default_gitconfig: GitConfig) -> GitConfig:
    """
    Use a clean and isolated default gitconfig avoiding user settings to break some tests.

    Add plumbum support to the original session-scoped fixture.
    """
    # local.env is a snapshot frozen at Python startup requiring its own monkeypatching
    for var in list(local.env.keys()):
        if var.startswith("GIT_"):
            del local.env[var]
    local.env["GIT_CONFIG_GLOBAL"] = str(default_gitconfig)
    default_gitconfig.set({"core.autocrlf": "input"})
    return default_gitconfig


@pytest.fixture
def gitconfig(gitconfig: GitConfig) -> Iterator[GitConfig]:
    """
    Use a clean and isolated gitconfig to test some specific user settings.

    Add plumbum support to the original function-scoped fixture.
    """
    with local.env(GIT_CONFIG_GLOBAL=str(gitconfig)):
        yield gitconfig
