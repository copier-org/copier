import re

from .helpers import render


def test_output(capsys, dst):
    render(dst, quiet=False)
    out, _ = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", out)
    assert re.search(r"create[^\s]*  pyproject\.toml", out)
    assert re.search(r"create[^\s]*  doc/images/nslogo\.gif", out)


def test_output_pretend(capsys, dst):
    render(dst, quiet=False, pretend=True)
    out, _ = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", out)
    assert re.search(r"create[^\s]*  pyproject\.toml", out)
    assert re.search(r"create[^\s]*  doc/images/nslogo\.gif", out)


def test_output_force(capsys, dst):
    render(dst)
    out, _ = capsys.readouterr()
    render(dst, quiet=False, force=True)
    out, _ = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", out)
    assert re.search(r"force[^\s]*  config\.py", out)
    assert re.search(r"identical[^\s]*  pyproject\.toml", out)
    assert re.search(r"identical[^\s]*  doc/images/nslogo\.gif", out)


def test_output_skip(capsys, dst):
    render(dst)
    out, _ = capsys.readouterr()
    render(dst, quiet=False, skip=True)
    out, _ = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", out)
    assert re.search(r"skip[^\s]*  config\.py", out)
    assert re.search(r"identical[^\s]*  pyproject\.toml", out)
    assert re.search(r"identical[^\s]*  doc/images/nslogo\.gif", out)


def test_output_quiet(capsys, dst):
    render(dst, quiet=True)
    out, _ = capsys.readouterr()
    assert out == ""
