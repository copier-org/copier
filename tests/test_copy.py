import os
import sys
from pathlib import Path

import pytest

import copier

from .helpers import DATA, PROJECT_TEMPLATE, assert_file, filecmp, render


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


def test_exclude_file(tmp_path):
    print(f"Filesystem encoding is {sys.getfilesystemencoding()}")
    # This file name is b"man\xcc\x83ana.txt".decode()
    render(tmp_path, exclude=["mañana.txt"])
    assert not (tmp_path / "doc" / "mañana.txt").exists()
    # This file name is b"ma\xc3\xb1ana.txt".decode()
    assert (tmp_path / "doc" / "mañana.txt").exists()
    assert (tmp_path / "doc" / "manana.txt").exists()


def test_skip_if_exists(tmp_path):
    copier.copy("tests/demo_skip_dst", tmp_path)
    copier.copy(
        "tests/demo_skip_src",
        tmp_path,
        skip_if_exists=["b.noeof.txt", "meh/c.noeof.txt"],
        force=True,
    )

    assert (tmp_path / "a.noeof.txt").read_text() == "OVERWRITTEN"
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
    assert (tmp_path / "a.noeof.txt").read_text() == "OVERWRITTEN"
    assert (tmp_path / "b.noeof.txt").read_text() == "OVERWRITTEN"
    assert (tmp_path / "meh" / "c.noeof.txt").read_text() == "SKIPPED"


def test_config_exclude(tmp_path, monkeypatch):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["*.txt"]}

    monkeypatch.setattr(copier.config.factory, "load_config_data", fake_data)
    copier.copy(str(PROJECT_TEMPLATE), tmp_path, data=DATA, quiet=True)
    assert not (tmp_path / "aaaa.txt").exists()


def test_config_exclude_overridden(tmp_path):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["*.txt"]}

    copier.copy(str(PROJECT_TEMPLATE), tmp_path, data=DATA, quiet=True, exclude=[])
    assert (tmp_path / "aaaa.txt").exists()


def test_config_include(tmp_path, monkeypatch):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["!.svn"]}

    monkeypatch.setattr(copier.config.factory, "load_config_data", fake_data)
    copier.copy(str(PROJECT_TEMPLATE), tmp_path, data=DATA, quiet=True)
    assert (tmp_path / ".svn").exists()


def test_skip_option(tmp_path):
    render(tmp_path)
    path = tmp_path / "pyproject.toml"
    content = "lorem ipsum"
    path.write_text(content)
    render(tmp_path, skip=True)
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


def test_subdirectory(tmp_path: Path):
    render(tmp_path, subdirectory="doc")
    assert not (tmp_path / "doc").exists()
    assert not (tmp_path / "config.py").exists()
    assert (tmp_path / "images").exists()
    assert (tmp_path / "manana.txt").exists()
