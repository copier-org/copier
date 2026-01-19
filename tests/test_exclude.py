import platform
from collections.abc import Mapping
from pathlib import Path

import pytest

from copier._main import run_copy
from copier._template import DEFAULT_EXCLUDE
from copier._types import StrOrPath

from .helpers import PROJECT_TEMPLATE, build_file_tree


def test_exclude_recursive(tmp_path: Path) -> None:
    """Copy is done properly when excluding recursively."""
    src = f"{PROJECT_TEMPLATE}_exclude"
    run_copy(src, tmp_path)
    assert not (tmp_path / "bad").exists()
    assert not (tmp_path / "bad").is_dir()


def test_exclude_recursive_negate(tmp_path: Path) -> None:
    """Copy is done properly when copy_me.txt is the sole file copied."""
    src = f"{PROJECT_TEMPLATE}_exclude_negate"
    run_copy(src, tmp_path)
    assert (tmp_path / "copy_me.txt").exists()
    assert (tmp_path / "copy_me.txt").is_file()
    assert not (tmp_path / "do_not_copy_me.txt").exists()


def test_config_exclude(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "copier.yml": "_exclude: ['*.txt']", src / "aaaa.txt": ""})
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "aaaa.txt").exists()
    assert (dst / "copier.yml").exists()


def test_config_exclude_extended(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "copier.yml": "_exclude: ['*.txt']", src / "aaaa.txt": ""})
    run_copy(str(src), dst, quiet=True, exclude=["*.yml"])
    assert not (dst / "aaaa.txt").exists()
    assert not (dst / "copier.yml").exists()


def test_config_include(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {src / "copier.yml": "_exclude: ['!.svn']", src / ".svn" / "hello": ""}
    )
    run_copy(str(src), dst, quiet=True)
    assert (dst / ".svn" / "hello").exists()
    assert (dst / "copier.yml").exists()


@pytest.mark.xfail(
    condition=platform.system() == "Darwin",
    reason="OS without proper UTF-8 filesystem.",
    strict=True,
)
def test_path_filter(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    file_excluded: Mapping[StrOrPath, bool] = {
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
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
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
                """
            ),
            **{(src / key): str(value) for key, value in file_excluded.items()},
        }
    )
    run_copy(str(src), dst)
    for key, value in file_excluded.items():
        assert (dst / key).exists() != value


def test_config_exclude_with_subdirectory(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Default excludes are not applied when a (true) subdirectory is specified."""
    # Make sure the file under test is in the list of default excludes
    assert "copier.yml" in DEFAULT_EXCLUDE

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "_subdirectory: 'template'",
            src / "template" / "copier.yml": "",
        }
    )
    run_copy(str(src), dst, quiet=True)
    assert (dst / "copier.yml").exists()


def test_config_exclude_with_subdirectory_dot(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Default excludes are applied when subdirectory is `.`."""
    # Make sure the file under test is in the list of default excludes
    assert "copier.yml" in DEFAULT_EXCLUDE

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {src / "copier.yml": "_subdirectory: '.'", src / "template" / "copier.yml": ""}
    )
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "template" / "copier.yml").exists()


def test_config_exclude_with_subdirectory_empty_string(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Default excludes are applied when subdirectory is `""`."""
    # Make sure the file under test is in the list of default excludes
    assert "copier.yml" in DEFAULT_EXCLUDE

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {src / "copier.yml": "_subdirectory: ''", src / "template" / "copier.yml": ""}
    )
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "template" / "copier.yml").exists()


def test_config_exclude_without_subdirectory(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Default excludes are applied when no subdirectory is specified."""
    # Make sure the file under test is in the list of default excludes
    assert "copier.yml" in DEFAULT_EXCLUDE

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "copier.yml": "", src / "template" / "copier.yml": ""})
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "template" / "copier.yml").exists()


def test_config_exclude_copieryml_without_templates_suffix(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _subdirectory: .
                _templates_suffix: ""
                _envops:
                    block_start_string: "[?"
                    block_end_string: "?]"
                """
            ),
        }
    )
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "copier.yml").exists()


def test_config_exclude_file_with_bad_jinja_syntax_without_templates_suffix(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _subdirectory: .
                _templates_suffix: ""
                _exclude:
                    - copier.yml
                    - exclude-me.txt
                """
            ),
            (src / "exclude-me.txt"): (
                """\
                "{%" is malformed Jinja syntax but it doesn't matter because
                this file is excluded
                """
            ),
        }
    )
    run_copy(str(src), dst, quiet=True)
    assert not (dst / "copier.yml").exists()
    assert not (dst / "exclude-me.txt").exists()


def test_config_exclude_with_templated_path(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _exclude:
                    - "*"
                    - "!keep-me.txt"

                filename_keep: keep-me.txt
                filename_exclude: exclude-me.txt
                """
            ),
            (src / "{{ filename_keep }}.jinja"): "",
            (src / "{{ filename_exclude }}.jinja"): "",
        }
    )
    run_copy(str(src), dst, defaults=True, quiet=True)
    assert (dst / "keep-me.txt").exists()
    assert not (dst / "exclude-me.txt").exists()


def test_exclude_wildcard_negate_nested_file(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test wildcard exclude with negated nested file and symlink excludes."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _preserve_symlinks: true
                _exclude:
                    - "*"
                    - "!/foo/keep-me.txt"
                    - "!/foo/bar/keep-me-symlink.txt"
                """
            ),
            (src / "exclude-me.txt"): "",
            (src / "foo" / "keep-me.txt"): "",
            (src / "foo" / "bar" / "keep-me-symlink.txt"): Path("..", "keep-me.txt"),
        }
    )
    run_copy(str(src), dst)
    assert (dst / "foo" / "keep-me.txt").exists()
    assert (dst / "foo" / "keep-me.txt").is_file()
    assert (dst / "foo" / "bar" / "keep-me-symlink.txt").exists()
    assert (dst / "foo" / "bar" / "keep-me-symlink.txt").is_symlink()
    assert (dst / "foo" / "bar" / "keep-me-symlink.txt").readlink() == Path(
        "..", "keep-me.txt"
    )
    assert not (dst / "exclude-me.txt").exists()
