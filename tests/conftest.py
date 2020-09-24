"""Special pytest configurations and fixtures."""

from typing import Generator

import pytest
from prompt_toolkit.application import AppSession, create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput


@pytest.fixture
def fake_tty() -> Generator[AppSession, None, None]:
    """Create a dummy TTy to test Copier behavior."""
    with create_app_session(input=create_pipe_input(), output=DummyOutput()) as session:
        yield session
