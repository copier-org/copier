import os
import platform
import sys
from pathlib import Path

import pytest
from plumbum import local
from plumbum.cmd import git

import copier

from .helpers import PROJECT_TEMPLATE, assert_file, build_file_tree, filecmp, render


def test_project_not_found(tmp_path):
    with pytest.raises(ValueError):
        copier.copy("foobar", tmp_path)

    with pytest.raises(ValueError):
        copier.copy(__file__, tmp_path)


def test_copy(tmp_path):
    render(tmp_path)

    generated = (tmp_path / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "reference_files/pyproject.toml").read_text()
    assert generated == control

    assert_file(tmp_path, "doc", "mañana.txt")
    assert_file(tmp_path, "doc", "images", "nslogo.gif")

    p1 = str(tmp_path / "awesome" / "hello.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]]" / "hello.txt")
    assert filecmp.cmp(p1, p2)

    with open(tmp_path / "README.txt") as readme:
        assert readme.read() == "This is the README for Copier.\n"

    p1 = str(tmp_path / "awesome.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]].txt")
    assert filecmp.cmp(p1, p2)

    assert not os.path.exists(tmp_path / "[% if not py3 %]py2_only.py[% endif %]")
    assert not os.path.exists(tmp_path / "[% if py3 %]py3_only.py[% endif %]")
    assert not os.path.exists(tmp_path / "py2_only.py")
    assert os.path.exists(tmp_path / "py3_only.py")
    assert not os.path.exists(
        tmp_path / "[% if not py3 %]py2_folder[% endif %]" / "thing.py"
    )
    assert not os.path.exists(
        tmp_path / "[% if py3 %]py3_folder[% endif %]" / "thing.py"
    )
    assert not os.path.exists(tmp_path / "py2_folder" / "thing.py")
    assert os.path.exists(tmp_path / "py3_folder" / "thing.py")


def test_copy_repo(tmp_path):
    copier.copy(
        "gh:copier-org/copier.git",
        tmp_path,
        vcs_ref="HEAD",
        quiet=True,
        exclude=["*", "!README.*"],
    )
    assert (tmp_path / "README.md").exists()


def test_default_exclude(tmp_path):
    render(tmp_path)
    assert not (tmp_path / ".svn").exists()


def test_include_file(tmp_path):
    render(tmp_path, exclude=["!.svn"])
    assert_file(tmp_path, ".svn")


def test_include_pattern(tmp_path):
    render(tmp_path, exclude=["!.*"])
    assert (tmp_path / ".svn").exists()


@pytest.mark.xfail(
    condition=platform.system() == "Darwin",
    reason="Mac claims to use UTF-8 filesystem, but behaves differently.",
    strict=True,
)
def test_exclude_file(tmp_path):
    print(f"Filesystem encoding is {sys.getfilesystemencoding()}")
    # This file name is b"man\xcc\x83ana.txt".decode()
    render(tmp_path, exclude=["mañana.txt"])
    assert not (tmp_path / "doc" / "mañana.txt").exists()
    # This file name is b"ma\xc3\xb1ana.txt".decode()
    assert (tmp_path / "doc" / "mañana.txt").exists()
    assert (tmp_path / "doc" / "manana.txt").exists()


def test_exclude_extends(tmp_path: Path):
    """Exclude argument extends the original exclusions instead of replacing them."""
    src, dst = tmp_path / "src", tmp_path / "dst"
    build_file_tree({src / "test.txt": "Test text", src / "test.json": '"test json"'})
    # Convert to git repo
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "hello world")
    copier.copy(str(src), str(dst), exclude=["*.txt"])
    assert (dst / "test.json").is_file()
    assert not (dst / "test.txt").exists()
    # .git exists in src, but not in dst because it is excluded by default
    assert not (dst / ".git").exists()


def test_exclude_replaces(tmp_path: Path):
    """Exclude in copier.yml replaces default values."""
    src, dst = tmp_path / "src", tmp_path / "dst"
    build_file_tree(
        {
            src / "test.txt": "Test text",
            src / "test.json": '"test json"',
            src / "test.yaml": '"test yaml"',
            src / "copier.yaml.tmpl": "purpose: template inception",
            src / "copier.yml": "_exclude: ['*.json']",
        }
    )
    copier.copy(str(src), str(dst), exclude=["*.txt"])
    assert (dst / "test.yaml").is_file()
    assert not (dst / "test.txt").exists()
    assert not (dst / "test.json").exists()
    assert (dst / "copier.yml").exists()
    assert (dst / "copier.yaml").is_file()


def test_skip_if_exists(tmp_path):
    copier.copy("tests/demo_skip_dst", tmp_path)
    copier.copy(
        "tests/demo_skip_src",
        tmp_path,
        skip_if_exists=["b.noeof.txt", "meh/c.noeof.txt"],
        force=True,
    )

    assert (tmp_path / "a.noeof.txt").read_text() == "SKIPPED"
    assert (tmp_path / "b.noeof.txt").read_text() == "SKIPPED"
    assert (tmp_path / "meh" / "c.noeof.txt").read_text() == "SKIPPED"


def test_skip_if_exists_rendered_patterns(tmp_path):
    copier.copy("tests/demo_skip_dst", tmp_path)
    copier.copy(
        "tests/demo_skip_src",
        tmp_path,
        data={"name": "meh"},
        skip_if_exists=["[[ name ]]/c.noeof.txt"],
        force=True,
    )
    assert (tmp_path / "a.noeof.txt").read_text() == "SKIPPED"
    assert (tmp_path / "b.noeof.txt").read_text() == "OVERWRITTEN"
    assert (tmp_path / "meh" / "c.noeof.txt").read_text() == "SKIPPED"


def test_skip_option(tmp_path):
    render(tmp_path)
    path = tmp_path / "pyproject.toml"
    content = "lorem ipsum"
    path.write_text(content)
    render(tmp_path, skip_if_exists=["**"])
    assert path.read_text() == content


def test_force_option(tmp_path):
    render(tmp_path)
    path = tmp_path / "pyproject.toml"
    content = "lorem ipsum"
    path.write_text(content)
    render(tmp_path, force=True)
    assert path.read_text() != content


def test_pretend_option(tmp_path):
    render(tmp_path, pretend=True)
    assert not (tmp_path / "doc").exists()
    assert not (tmp_path / "config.py").exists()
    assert not (tmp_path / "pyproject.toml").exists()


@pytest.mark.parametrize("generate", (True, False))
def test_empty_dir(tmp_path_factory, generate):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yaml": """
                _subdirectory: tpl
                _templates_suffix: .jinja
                do_it:
                    type: bool
            """,
            src
            / "tpl"
            / "[% if do_it %]one_dir[% endif %]"
            / "one.txt.jinja": "[[ do_it ]]",
            src / "tpl" / "two.txt": "[[ do_it ]]",
            src / "tpl" / "[% if do_it %]three.txt[% endif %].jinja": "[[ do_it ]]",
            src
            / "tpl"
            / "four"
            / "[% if do_it %]five.txt[% endif %].jinja": "[[ do_it ]]",
        },
    )
    copier.run_copy(str(src), dst, {"do_it": generate}, force=True)
    assert (dst / "four").is_dir()
    assert (dst / "two.txt").read_text() == "[[ do_it ]]"
    assert (dst / "one_dir").exists() == generate
    assert (dst / "three.txt").exists() == generate
    assert (dst / "one_dir").is_dir() == generate
    assert (dst / "one_dir" / "one.txt").is_file() == generate
    if generate:
        assert (dst / "one_dir" / "one.txt").read_text() == repr(generate)
        assert (dst / "three.txt").read_text() == repr(generate)
        assert (dst / "four" / "five.txt").read_text() == repr(generate)
