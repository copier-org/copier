from pathlib import Path

import pytest
from poethepoet.app import PoeThePoet

from copier import tools
from copier.config.factory import ConfigData, EnvOps

from .helpers import DATA, PROJECT_TEMPLATE


def test_render(tmp_path):
    envops = EnvOps().dict()
    render = tools.Renderer(
        ConfigData(
            src_path=PROJECT_TEMPLATE,
            dst_path=tmp_path,
            data_from_init=DATA,
            envops=envops,
        )
    )

    assert render.string("/hello/[[ what ]]/") == "/hello/world/"
    assert render.string("/hello/world/") == "/hello/world/"

    sourcepath = PROJECT_TEMPLATE / "pyproject.toml.tmpl"
    result = render(sourcepath)
    expected = Path("./tests/reference_files/pyproject.toml").read_text()
    assert result == expected


TEST_PATTERNS = (
    # simple file patterns and their negations
    "*.exclude",
    "!do_not.exclude",
    # dir patterns and their negations
    "exclude_dir/",
    "!exclude_dir/please_copy_me",
    "!not_exclude_dir/x",
    # unicode patterns
    "mañana.txt",
)
path_filter = tools.create_path_filter(TEST_PATTERNS)


@pytest.mark.parametrize(
    "pattern,should_match",
    (
        # simple file patterns and their negations
        ("x.exclude", True),
        ("do_not.exclude!", False),
        # dir patterns and their negations
        ("exclude_dir/x", True),
        ("exclude_dir/please_copy_me", False),  # no mercy
        ("not_exclude_dir/x!", False),
        # unicode patterns
        ("mañana.txt", True),
        ("mañana.txt", False),
        ("manana.txt", False),
    ),
)
def test_create_path_filter(pattern, should_match):
    assert path_filter(pattern) == should_match


def test_lint():
    """Ensure source code formatting"""
    PoeThePoet(Path("."))(["lint", "--show-diff-on-failure", "--color=always"])


def test_types():
    """Ensure source code static typing."""
    PoeThePoet(Path("."))(["types"])
