from pathlib import Path

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


def test_path_filter(tmp_path_factory):
    src, dst = tmp_path_factory.mktemp("src"), tmp_path_factory.mktemp("dst")
    file_excluded = {
        "x.exclude": True,
        "do_not.exclude!": False,
        # dir patterns and their negations
        Path("exclude_dir", "x"): True,
        Path("exclude_dir", "please_copy_me"): False,  # no mercy
        Path("not_exclude_dir", "x!"): False,
        # unicode patterns
        "mañana.txt": True,
        "mañana.txt": False,
        "manana.txt": False,
    }
    file_tree_spec = {
        src
        / "copier.yaml": """
            _exclude:
                # simple file patterns and their negations
                - "*.exclude"
                - "!do_not.exclude"
                # dir patterns and their negations
                - "exclude_dir/"
                - "!exclude_dir/please_copy_me"
                - "!not_exclude_dir/x"
                # unicode patterns
                - "mañana.txt"
            """,
    }
    for key, value in file_excluded.items():
        file_tree_spec[src / key] = str(value)
    build_file_tree(file_tree_spec)
    copy(str(src), dst)
    for key, value in file_excluded.items():
        assert (dst / key).exists() != value
