import os
import sys
from pathlib import Path

import pytest

import copier

from .helpers import DATA, PROJECT_TEMPLATE, assert_file, filecmp, render


def test_project_not_found(dst):
    with pytest.raises(ValueError):
        copier.copy("foobar", dst)

    with pytest.raises(ValueError):
        copier.copy(__file__, dst)


def test_copy(dst):
    render(dst)

    generated = (dst / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "reference_files/pyproject.toml").read_text()
    assert generated == control

    assert_file(dst, "doc", "mañana.txt")
    assert_file(dst, "doc", "images", "nslogo.gif")

    p1 = str(dst / "awesome" / "hello.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]]" / "hello.txt")
    assert filecmp.cmp(p1, p2)

    with open(dst / "README.txt") as readme:
        assert readme.read() == "This is the README for Copier.\n"

    p1 = str(dst / "awesome.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]].txt")
    assert filecmp.cmp(p1, p2)

    assert not os.path.exists(dst / "[% if not py3 %]py2_only.py[% endif %]")
    assert not os.path.exists(dst / "[% if py3 %]py3_only.py[% endif %]")
    assert not os.path.exists(dst / "py2_only.py")
    assert os.path.exists(dst / "py3_only.py")
    assert not os.path.exists(
        dst / "[% if not py3 %]py2_folder[% endif %]" / "thing.py"
    )
    assert not os.path.exists(dst / "[% if py3 %]py3_folder[% endif %]" / "thing.py")
    assert not os.path.exists(dst / "py2_folder" / "thing.py")
    assert os.path.exists(dst / "py3_folder" / "thing.py")


def test_copy_repo(dst):
    copier.copy("gh:jpscaletti/siht.git", dst, vcs_ref="HEAD", quiet=True)
    assert (dst / "setup.py").exists()


def test_default_exclude(dst):
    render(dst)
    assert not (dst / ".svn").exists()


def test_include_file(dst):
    render(dst, exclude=["!.svn"])
    assert_file(dst, ".svn")


def test_include_pattern(dst):
    render(dst, exclude=["!.*"])
    assert (dst / ".svn").exists()


def test_exclude_file(tmp_path):
    print(f"Filesystem encoding is {sys.getfilesystemencoding()}")
    # This file name is b"man\xcc\x83ana.txt".decode()
    render(tmp_path, exclude=["mañana.txt"])
    assert not (tmp_path / "doc" / "mañana.txt").exists()
    # This file name is b"ma\xc3\xb1ana.txt".decode()
    assert (tmp_path / "doc" / "mañana.txt").exists()
    assert (tmp_path / "doc" / "manana.txt").exists()


def test_skip_if_exists(dst):
    copier.copy("tests/demo_skip_dst", dst)
    copier.copy(
        "tests/demo_skip_src",
        dst,
        skip_if_exists=["b.noeof.txt", "meh/c.noeof.txt"],
        force=True,
    )

    assert (dst / "a.noeof.txt").read_text() == "OVERWRITTEN"
    assert (dst / "b.noeof.txt").read_text() == "SKIPPED"
    assert (dst / "meh" / "c.noeof.txt").read_text() == "SKIPPED"


def test_skip_if_exists_rendered_patterns(dst):
    copier.copy("tests/demo_skip_dst", dst)
    copier.copy(
        "tests/demo_skip_src",
        dst,
        data={"name": "meh"},
        skip_if_exists=["[[ name ]]/c.noeof.txt"],
        force=True,
    )
    assert (dst / "a.noeof.txt").read_text() == "OVERWRITTEN"
    assert (dst / "b.noeof.txt").read_text() == "OVERWRITTEN"
    assert (dst / "meh" / "c.noeof.txt").read_text() == "SKIPPED"


def test_config_exclude(dst, monkeypatch):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["*.txt"]}

    monkeypatch.setattr(copier.config.factory, "load_config_data", fake_data)
    copier.copy(str(PROJECT_TEMPLATE), dst, data=DATA, quiet=True)
    assert not (dst / "aaaa.txt").exists()


def test_config_exclude_overridden(dst):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["*.txt"]}

    copier.copy(str(PROJECT_TEMPLATE), dst, data=DATA, quiet=True, exclude=[])
    assert (dst / "aaaa.txt").exists()


def test_config_include(dst, monkeypatch):
    def fake_data(*_args, **_kwargs):
        return {"_exclude": ["!.svn"]}

    monkeypatch.setattr(copier.config.factory, "load_config_data", fake_data)
    copier.copy(str(PROJECT_TEMPLATE), dst, data=DATA, quiet=True)
    assert (dst / ".svn").exists()


def test_skip_option(dst):
    render(dst)
    path = dst / "pyproject.toml"
    content = "lorem ipsum"
    path.write_text(content)
    render(dst, skip=True)
    assert path.read_text() == content


def test_force_option(dst):
    render(dst)
    path = dst / "pyproject.toml"
    content = "lorem ipsum"
    path.write_text(content)
    render(dst, force=True)
    assert path.read_text() != content


def test_pretend_option(dst):
    render(dst, pretend=True)
    assert not (dst / "doc").exists()
    assert not (dst / "config.py").exists()
    assert not (dst / "pyproject.toml").exists()


def test_subdirectory(tmp_path: Path):
    render(tmp_path, subdirectory="doc")
    assert not (tmp_path / "doc").exists()
    assert not (tmp_path / "config.py").exists()
    assert (tmp_path / "images").exists()
    assert (tmp_path / "manana.txt").exists()
