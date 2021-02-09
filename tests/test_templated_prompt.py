from datetime import datetime

import pexpect
import pytest
import yaml

from copier import Worker
from copier.errors import InvalidTypeError

from .helpers import COPIER_PATH, ISOFORMAT, build_file_tree

envops = {}
main_default = "copier"
main_question = {"main": {"default": main_default}}


@pytest.mark.parametrize(
    "questions_data, expected_value, expected_outputs",
    [
        (
            {"templated_default": {"default": "[[ main ]]default"}},
            "copierdefault",
            ["[copierdefault]"],
        ),
        (
            {
                "templated_type": {
                    "type": "[% if main == 'copier' %]int[% endif %]",
                    "default": "0",
                },
            },
            0,
            ["Format: int", "[0]"],
        ),
        (
            {
                "templated_help": {
                    "default": main_default,
                    "help": "THIS [[ main ]] HELP IS TEMPLATED",
                },
            },
            main_default,
            ["THIS copier HELP IS TEMPLATED"],
        ),
        (
            {
                "templated_choices_dict_1": {
                    "default": "[[ main ]]",
                    "choices": {"choice 1": "[[ main ]]", "[[ main ]]": "value 2"},
                },
            },
            main_default,
            ["choice 1", "copier"],
        ),
        (
            {
                "templated_choices_dict_2": {
                    "default": "value 2",
                    "choices": {"choice 1": "[[ main ]]", "[[ main ]]": "value 2"},
                },
            },
            "value 2",
            ["(1) choice 1", "(2) copier", "Choice [2]"],
        ),
        (
            {
                "templated_choices_string_list_1": {
                    "default": main_default,
                    "choices": ["[[ main ]]", "choice 2"],
                },
            },
            main_default,
            ["(1) copier", "(2) choice 2", "Choice [1]"],
        ),
        (
            {
                "templated_choices_string_list_2": {
                    "default": "choice 1",
                    "choices": ["choice 1", "[[ main ]]"],
                },
            },
            "choice 1",
            ["(1) choice 1", "(2) copier", "Choice [1]"],
        ),
        (
            {
                "templated_choices_tuple_list_1": {
                    "default": main_default,
                    "choices": [["name 1", "[[ main ]]"], ["[[ main ]]", "value 2"]],
                },
            },
            main_default,
            ["(1) name 1", "(2) copier", "Choice [1]"],
        ),
        (
            {
                "templated_choices_tuple_list_2": {
                    "default": "value 2",
                    "choices": [["name 1", "[[ main ]]"], ["[[ main ]]", "value 2"]],
                },
            },
            "value 2",
            ["name 1", "copier"],
        ),
        (
            {
                "templated_choices_mixed_list": {
                    "default": "value 2",
                    "choices": ["[[ main ]]", ["[[ main ]]", "value 2"]],
                },
            },
            "value 2",
            ["copier", "copier"],
        ),
    ],
)
def test_templated_prompt(
    questions_data, expected_value, expected_outputs, tmp_path_factory, spawn
):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    questions_combined = {**main_question, **questions_data}
    # There's always only 1 question; get its name
    question_name = questions_data.copy().popitem()[0]
    build_file_tree(
        {
            template / "copier.yml": yaml.dump(questions_combined),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn([COPIER_PATH, str(template), str(subproject)], timeout=10)
    tui.expect_exact(["main?", "Format: yaml", main_default])
    tui.sendline()
    tui.expect_exact([f"{question_name}?"] + expected_outputs)
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers[question_name] == expected_value


def test_templated_prompt_custom_envops(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """
                _envops:
                    block_start_string: "<%"
                    block_end_string: "%>"
                    comment_start_string: "<#"
                    comment_end_string: "#>"
                    variable_start_string: "<<"
                    variable_end_string: ">>"

                powerlevel:
                    type: int
                    default: 9000

                sentence:
                    type: str
                    default:
                        "<% if powerlevel >= 9000 %>It's over 9000!<% else %>It's only << powerlevel >>...<%
                        endif %>"
            """,
            src / "result.tmpl": "<<sentence>>",
        }
    )
    worker1 = Worker(str(src), dst, force=True)
    worker1.run_copy()
    assert (dst / "result").read_text() == "It's over 9000!"

    worker2 = Worker(str(src), dst, data={"powerlevel": 1}, force=True)
    worker2.run_copy()
    assert (dst / "result").read_text() == "It's only 1..."


def test_templated_prompt_builtins(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yaml": """
                question1:
                    default: "[[ now() ]]"
                question2:
                    default: "[[ make_secret() ]]"
            """,
            src / "now.tmpl": "[[ question1 ]]",
            src / "make_secret.tmpl": "[[ question2 ]]",
        }
    )
    Worker(str(src), dst, force=True).run_copy()
    that_now = datetime.strptime((dst / "now").read_text(), ISOFORMAT)
    assert that_now <= datetime.now()
    assert len((dst / "make_secret").read_text()) == 128


@pytest.mark.parametrize(
    "questions, raises, returns",
    (
        ({"question": {"default": "[[ not_valid ]]"}}, None, ""),
        ({"question": {"help": "[[ not_valid ]]"}}, None, "None"),
        ({"question": {"type": "[[ not_valid ]]"}}, InvalidTypeError, "None"),
        ({"question": {"choices": ["[[ not_valid ]]"]}}, None, "None"),
    ),
)
def test_templated_prompt_invalid(tmp_path_factory, questions, raises, returns):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": yaml.safe_dump(questions),
            src / "result.tmpl": "[[question]]",
        }
    )
    worker = Worker(str(src), dst, force=True)
    if raises:
        with pytest.raises(raises):
            worker.run_copy()
    else:
        worker.run_copy()
        assert (dst / "result").read_text() == returns
