import platform
import sys
from typing import Optional, Tuple

import pytest
from coverage.tracer import CTracer
from pexpect.popen_spawn import PopenSpawn

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

    def _spawn(cmd: Tuple[str, ...], *, timeout: Optional[int] = None) -> PopenSpawn:
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
