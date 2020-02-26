from copier.main import copy

from .helpers import PROJECT_TEMPLATE


def test_exclude_recursive(tmp_path):
    """Copy is done properly when excluding recursively."""
    src = f"{PROJECT_TEMPLATE}_exclude"
    copy(src, tmp_path)
    assert not (tmp_path / "bad").exists()
    assert not (tmp_path / "bad").is_dir()


def test_exclude_recursive_negate(tmp_path):
    """Copy is done properly when excluding recursively."""
    src = f"{PROJECT_TEMPLATE}_exclude_negate"
    copy(src, tmp_path)
    assert (tmp_path / "bad").exists()
    assert (tmp_path / "bad").is_dir()
