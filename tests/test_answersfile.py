from textwrap import dedent

import copier
from copier.config.user_data import load_answersfile_data

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_answersfile"


def test_answersfile(dst):
    """Test copier behaves properly when using an answersfile."""
    round_file = dst / "round.txt"

    # Check 1st round is properly executed and remembered
    copier.copy(SRC, dst, force=True)
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
    log = load_answersfile_data(dst)
    assert log["round"] == "1st"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log

    # Check 2nd round is properly executed and remembered
    copier.copy(SRC, dst, {"round": "2nd"}, force=True)
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
    log = load_answersfile_data(dst)
    assert log["round"] == "2nd"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log

    # Check repeating 2nd is properly executed and remembered
    copier.copy(SRC, dst, force=True)
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
    log = load_answersfile_data(dst)
    assert log["round"] == "2nd"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log
