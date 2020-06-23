from subprocess import CalledProcessError

import pytest

import copier


def test_cleanup(tmp_path):
    with pytest.raises(CalledProcessError):
        copier.copy("./tests/demo_cleanup", tmp_path, quiet=True)
    assert not (tmp_path).exists()


def test_do_not_cleanup(tmp_path):
    with pytest.raises(CalledProcessError):
        copier.copy(
            "./tests/demo_cleanup", tmp_path, quiet=True, cleanup_on_error=False
        )
    assert (tmp_path).exists()
