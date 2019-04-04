import re

from .helpers import render


def test_output(capsys, dst):
    render(dst, quiet=False)
    out, err = capsys.readouterr()
    print(out)
    assert re.search(r"create  config\.py", out)
    assert re.search(r"create  pyproject\.toml", out)
    assert re.search(r"create  doc/images/nslogo\.gif", out)


def test_output_pretend(capsys, dst):
    render(dst, quiet=False, pretend=True)
    out, err = capsys.readouterr()

    assert re.search(r"create  config\.py", out)
    assert re.search(r"create  pyproject\.toml", out)
    assert re.search(r"create  doc/images/nslogo\.gif", out)


def test_output_force(capsys, dst):
    render(dst)
    out, err = capsys.readouterr()
    render(dst, quiet=False, force=True)
    out, err = capsys.readouterr()
    print(out)

    assert re.search(r"conflict  config\.py", out)
    assert re.search(r"force  config\.py", out)
    assert re.search(r"identical  pyproject\.toml", out)
    assert re.search(r"identical  doc/images/nslogo\.gif", out)


def test_output_skip(capsys, dst):
    render(dst)
    out, err = capsys.readouterr()
    render(dst, quiet=False, skip=True)
    out, err = capsys.readouterr()
    print(out)

    assert re.search(r"conflict  config\.py", out)
    assert re.search(r"skip  config\.py", out)
    assert re.search(r"identical  pyproject\.toml", out)
    assert re.search(r"identical  doc/images/nslogo\.gif", out)


def test_output_quiet(capsys, dst):
    render(dst, quiet=True)
    out, err = capsys.readouterr()
    assert out == ""
