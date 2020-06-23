from textwrap import dedent

import pytest

import copier
from copier.config.user_data import load_answersfile_data

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_answersfile"


@pytest.mark.parametrize("answers_file", [None, ".changed-by-user.yaml"])
def test_answersfile(tmp_path, answers_file):
    """Test copier behaves properly when using an answersfile."""
    round_file = tmp_path / "round.txt"

    # Check 1st round is properly executed and remembered
    copier.copy(SRC, tmp_path, answers_file=answers_file, force=True)
    answers_file = answers_file or ".answers-file-changed-in-template.yml"
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 1st round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "1st"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log

    # Check 2nd round is properly executed and remembered
    copier.copy(SRC, tmp_path, {"round": "2nd"}, answers_file=answers_file, force=True)
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 2nd round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "2nd"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log

    # Check repeating 2nd is properly executed and remembered
    copier.copy(SRC, tmp_path, answers_file=answers_file, force=True)
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 2nd round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "2nd"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log
