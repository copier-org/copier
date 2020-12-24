from copier.main import copy

from .helpers import PROJECT_TEMPLATE, build_file_tree


def test_exclude_recursive(tmp_path):
    """Copy is done properly when excluding recursively."""
    src = f"{PROJECT_TEMPLATE}_exclude"
    copy(src, tmp_path)
    assert not (tmp_path / "bad").exists()
    assert not (tmp_path / "bad").is_dir()


def test_exclude_recursive_negate(tmp_path):
    """Copy is done properly when copy_me.txt is the sole file copied."""
    src = f"{PROJECT_TEMPLATE}_exclude_negate"
    copy(src, tmp_path)
    assert (tmp_path / "copy_me.txt").exists()
    assert (tmp_path / "copy_me.txt").is_file()
    assert not (tmp_path / "do_not_copy_me.txt").exists()


def test_config_exclude(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    build_file_tree({src / "copier.yml": "_exclude: ['*.txt']", src / "aaaa.txt": ""})
    copy(str(src), dst, quiet=True)
    assert not (dst / "aaaa.txt").exists()
    assert (dst / "copier.yml").exists()


def test_config_exclude_extended(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    build_file_tree({src / "copier.yml": "_exclude: ['*.txt']", src / "aaaa.txt": ""})
    copy(str(src), dst, quiet=True, exclude=["*.yml"])
    assert not (dst / "aaaa.txt").exists()
    assert not (dst / "copier.yml").exists()


def test_config_include(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    build_file_tree(
        {src / "copier.yml": "_exclude: ['!.svn']", src / ".svn" / "hello": ""}
    )
    copy(str(src), dst, quiet=True)
    assert (dst / ".svn" / "hello").exists()
    assert (dst / "copier.yml").exists()
