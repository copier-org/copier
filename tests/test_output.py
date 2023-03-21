import re
from pathlib import Path

import pytest

from .helpers import render


def test_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=False)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_pretend(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=False, pretend=True)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_force(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, defaults=True, overwrite=True)
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"overwrite[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_skip(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, skip_if_exists=["config.py"])
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"skip[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_quiet(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=True)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
