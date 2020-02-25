from copier.main import copy

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_exclude"


def test_recursive_exclude(tmp_path):
    """Copy is done properly when excluding recursively."""
    copy(SRC, tmp_path)
    assert not (tmp_path / "bad").is_dir()
    assert not (tmp_path / "bad").exists()
