from textwrap import dedent

import pytest

import copier
from copier.user_data import load_answersfile_data

from .helpers import BRACKET_ENVOPS_JSON, CONFIG_DIR, SUFFIX_TMPL, build_file_tree


@pytest.fixture(scope="module")
def template_path(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root
            / CONFIG_DIR
            / "[[ _copier_conf.answers_file ]].tmpl": """\
                # Changes here will be overwritten by Copier
                [[ _copier_answers|to_nice_yaml ]]
                """,
            root
            / "copier.yml": f"""\
                _answers_file: .answers-file-changed-in-template.yml
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}

                round: 1st

                # A str question without a default should default to None
                str_question_without_default:
                    type: str

                # password_1 and password_2 must not appear in answers file
                _secret_questions:
                    - password_1

                password_1: password one
                password_2:
                    secret: yes
                    default: password two
                """,
            root
            / "round.txt.tmpl": """\
                It's the [[round]] round.
                password_1=[[password_1]]
                password_2=[[password_2]]
                """,
        }
    )
    return str(root)


@pytest.mark.parametrize("answers_file", [None, ".changed-by-user.yaml"])
def test_answersfile(template_path, tmp_path, answers_file):
    """Test copier behaves properly when using an answersfile."""
    round_file = tmp_path / "round.txt"

    # Check 1st round is properly executed and remembered
    copier.copy(
        template_path,
        tmp_path,
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
    )
    answers_file = answers_file or f"{CONFIG_DIR}/.answers-file-changed-in-template.yml"
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
    log = load_answersfile_data(tmp_path, answers_file, answers_file_folder=CONFIG_DIR)
    assert log["round"] == "1st"
    assert log["str_question_without_default"] is None
    assert "password_1" not in log
    assert "password_2" not in log

    # Check 2nd round is properly executed and remembered
    copier.copy(
        template_path,
        tmp_path,
        {"round": "2nd"},
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
        update_context=True,
    )
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
    copier.copy(
        template_path,
        tmp_path,
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
        update_context=True,
    )
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
