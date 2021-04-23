import platform
import sys

import pytest
from pexpect.popen_spawn import PopenSpawn


@pytest.fixture
def spawn():
    """Spawn a copier process TUI to interact with."""
    if platform.system() == "Windows":
        # HACK https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1243#issuecomment-706668723
        # FIXME Use pexpect or wexpect somehow to fix this
        pytest.xfail(
            "pexpect fails on Windows",
        )
    # Disable subprocess timeout if debugging, for commodity
    # See https://stackoverflow.com/a/67065084/1468388
    if getattr(sys, "gettrace", lambda: False):
        return lambda cmd, timeout=None, *args, **kwargs: PopenSpawn(
            cmd, None, *args, **kwargs
        )
    # Using PopenSpawn, although probably it would be best to use pexpect.spawn
    # instead. However, it's working fine and it seems easier to fix in the
    # future to work on Windows (where, this way, spawning actually works; it's just
    # python-prompt-toolkit that rejects displaying a TUI)
    return PopenSpawn
