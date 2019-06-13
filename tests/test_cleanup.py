from subprocess import CalledProcessError

import pytest

from .. import copier


def test_cleanup(dst):
    with pytest.raises(CalledProcessError):
        copier.copy("./tests/demo_cleanup", dst, quiet=True)
    assert not (dst).exists()


def test_do_not_cleanup(dst):
    with pytest.raises(CalledProcessError):
        copier.copy("./tests/demo_cleanup", dst, quiet=True, cleanup_on_error=False)
    assert (dst).exists()
