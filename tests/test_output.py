import re

from .helpers import render


def test_output(capsys, tmp_path):
    render(tmp_path, quiet=False)
    out, _ = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", out)
    assert re.search(r"create[^\s]*  pyproject\.toml", out)
    assert re.search(r"create[^\s]*  doc/images/nslogo\.gif", out)


def test_output_pretend(capsys, tmp_path):
    render(tmp_path, quiet=False, pretend=True)
    out, _ = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", out)
    assert re.search(r"create[^\s]*  pyproject\.toml", out)
    assert re.search(r"create[^\s]*  doc/images/nslogo\.gif", out)


def test_output_force(capsys, tmp_path):
    render(tmp_path)
    out, _ = capsys.readouterr()
    render(tmp_path, quiet=False, force=True)
    out, _ = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", out)
    assert re.search(r"force[^\s]*  config\.py", out)
    assert re.search(r"identical[^\s]*  pyproject\.toml", out)
    assert re.search(r"identical[^\s]*  doc/images/nslogo\.gif", out)


def test_output_skip(capsys, tmp_path):
    render(tmp_path)
    out, _ = capsys.readouterr()
    render(tmp_path, quiet=False, skip=True)
    out, _ = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", out)
    assert re.search(r"skip[^\s]*  config\.py", out)
    assert re.search(r"identical[^\s]*  pyproject\.toml", out)
    assert re.search(r"identical[^\s]*  doc/images/nslogo\.gif", out)


def test_output_quiet(capsys, tmp_path):
    render(tmp_path, quiet=True)
    out, _ = capsys.readouterr()
    assert out == ""
