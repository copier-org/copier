import re
from pathlib import Path

import pytest

from copier.errors import InvalidTypeError
from copier.main import run_copy

from .helpers import build_file_tree, render


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


def test_question_with_invalid_type(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            src
            / "copier.yaml": """
                bad:
                    type: invalid
                    default: 1
                """
        }
    )
    with pytest.raises(
        InvalidTypeError, match='Unsupported type "invalid" in question "bad"'
    ):
        run_copy(str(src), dst, defaults=True, overwrite=True)


def test_answer_with_invalid_type(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            src
            / "copier.yaml": """
                bad:
                    type: int
                    default: null
                """
        }
    )
    with pytest.raises(
        InvalidTypeError,
        match='Invalid answer "None" of type "<class \'NoneType\'>" to question "bad" of type "int"',
    ):
        run_copy(str(src), dst, defaults=True, overwrite=True)
