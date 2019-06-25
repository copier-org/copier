from pathlib import Path

import pytest

from .. import copier

from .helpers import (
    assert_file,
    render,
    PROJECT_TEMPLATE,
    DATA,
    filecmp,
)


def test_project_not_found(dst):
    with pytest.raises(ValueError):
        copier.copy("foobar", dst)

    with pytest.raises(ValueError):
        copier.copy(__file__, dst)


def test_copy(dst):
    render(dst)

    generated = (dst / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "pyproject.toml.ref").read_text()
    assert generated == control

    assert_file(dst, "doc", "mañana.txt")
    assert_file(dst, "doc", "images", "nslogo.gif")

    p1 = str(dst / "awesome" / "hello.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]]" / "hello.txt")
    assert filecmp.cmp(p1, p2)

    p1 = str(dst / "awesome.txt")
    p2 = str(PROJECT_TEMPLATE / "[[ myvar ]].txt")
    assert filecmp.cmp(p1, p2)


def test_copy_repo(dst):
    copier.copy("gh:jpscaletti/siht.git", dst, quiet=True)
    assert (dst / "setup.py").exists()


def test_default_exclude(dst):
    render(dst)
    assert not (dst / ".svn").exists()


def test_include_file(dst):
    render(dst, include=[".svn"])
    assert_file(dst, ".svn")


def test_include_pattern(dst):
    render(dst, include=[".*"])
    assert (dst / ".svn").exists()


def test_exclude_file(dst):
    render(dst, exclude=["mañana.txt"])
    assert not (dst / "doc" / "mañana.txt").exists()


def test_skip_if_exists(dst):
    copier.copy("tests/demo_skip_dst", dst)
    copier.copy(
        "tests/demo_skip_src",
        dst,
        skip_if_exists=["b.txt", "meh/c.txt"],
        force=True
    )

    assert (dst / "a.txt").read_text() == "OVERWRITTEN"
    assert (dst / "b.txt").read_text() == "SKIPPED"
    assert (dst / "meh" / "c.txt").read_text() == "SKIPPED"


def test_skip_if_exists_rendered_patterns(dst):
    copier.copy("tests/demo_skip_dst", dst)
    copier.copy(
        "tests/demo_skip_src",
        dst,
        data={"name": "meh"},
        skip_if_exists=["[[ name ]]/c.txt"],
        force=True
    )
    assert (dst / "a.txt").read_text() == "OVERWRITTEN"
    assert (dst / "b.txt").read_text() == "OVERWRITTEN"
    assert (dst / "meh" / "c.txt").read_text() == "SKIPPED"


def test_config_exclude(dst):
    def fake_data(*_args, **_kw):
        return {"_exclude": ["*.txt"]}

    copier.main._load_config_data = copier.main.load_config_data
    copier.main.load_config_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True)
    assert not (dst / "aaaa.txt").exists()
    copier.main.load_config_data = copier.main._load_config_data


def test_config_exclude_overridden(dst):
    def fake_data(*_args, **_kw):
        return {"_exclude": ["*.txt"]}

    copier.main._load_config_data = copier.main.load_config_data
    copier.main.load_config_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True, exclude=[])
    assert (dst / "aaaa.txt").exists()
    copier.main.load_config_data = copier.main._load_config_data


def test_config_include(dst):
    def fake_data(*_args, **_kw):
        return {"_include": [".svn"]}

    copier.main._load_config_data = copier.main.load_config_data
    copier.main.load_config_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True)
    assert (dst / ".svn").exists()
    copier.main.load_config_data = copier.main._load_config_data


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


def test_tasks(dst):
    tasks = ["touch [[ myvar ]]/1.txt", "touch [[ myvar ]]/2.txt"]
    render(dst, tasks=tasks)
    assert (dst / DATA["myvar"] / "1.txt").exists()
    assert (dst / DATA["myvar"] / "2.txt").exists()
