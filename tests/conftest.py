import platform

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
    # Using PopenSpawn, although probably it would be best to use pexpect.spawn
    # instead. However, it's working fine and it seems easier to fix in the
    # future to work on Windows (where, this way, spawning actually works; it's just
    # python-prompt-toolkit that rejects displaying a TUI)
    return PopenSpawn
