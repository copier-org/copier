import platform
import sys
from pathlib import Path

import pytest
from coverage.tracer import CTracer
from pexpect.popen_spawn import PopenSpawn
from plumbum.cmd import git


@pytest.fixture
def src_repo(tmp_path_factory) -> Path:
    """Quick helper to avoid creating template repo constantly."""
    result = tmp_path_factory.mktemp("src_repo")
    git("-C", result, "init")
    return result


@pytest.fixture
def spawn():
    """Spawn a copier process TUI to interact with."""
    if platform.system() == "Windows":
        # HACK https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1243#issuecomment-706668723
        # FIXME Use pexpect or wexpect somehow to fix this
        pytest.xfail(
            "pexpect fails on Windows",
        )
    # Disable subprocess timeout if debugging (except coverage), for commodity
    # See https://stackoverflow.com/a/67065084/1468388
    tracer = getattr(sys, "gettrace", lambda: None)()
    if not isinstance(tracer, (CTracer, type(None))):
        return lambda cmd, timeout=None, *args, **kwargs: PopenSpawn(
            cmd, None, *args, **kwargs
        )
    # Using PopenSpawn, although probably it would be best to use pexpect.spawn
    # instead. However, it's working fine and it seems easier to fix in the
    # future to work on Windows (where, this way, spawning actually works; it's just
    # python-prompt-toolkit that rejects displaying a TUI)
    return PopenSpawn
