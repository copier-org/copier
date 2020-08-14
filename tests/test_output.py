import re

from .helpers import render


def test_output(capsys, tmp_path):
    render(tmp_path, quiet=False)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_pretend(capsys, tmp_path):
    render(tmp_path, quiet=False, pretend=True)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_force(capsys, tmp_path):
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, force=True)
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"force[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_skip(capsys, tmp_path):
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, skip=True)
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"skip[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_quiet(capsys, tmp_path):
    render(tmp_path, quiet=True)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
