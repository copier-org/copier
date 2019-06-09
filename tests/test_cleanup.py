from pathlib import Path
from subprocess import CalledProcessError

import pytest

from .. import copier

from .helpers import assert_file, render, PROJECT_TEMPLATE, DATA, filecmp


@pytest.mark.slow
def test_cleanup(dst):
    with pytest.raises(CalledProcessError):
        copier.copy("./tests/demo_cleanup", dst, quiet=True)
    assert not (dst).exists()
