import pexpect
import pytest
import yaml

from copier.config.factory import filter_config, make_config
from copier.config.objects import EnvOps
from copier.config.user_data import InvalidTypeError, query_user_data

from .helpers import COPIER_PATH, build_file_tree

envops = EnvOps()
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
    questions_combined = filter_config({**main_question, **questions_data})[1]
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


def test_templated_prompt_custom_envops(tmp_path):
    conf = make_config("./tests/demo_templated_prompt", tmp_path, force=True)
    assert conf.data["sentence"] == "It's over 9000!"

    conf = make_config(
        "./tests/demo_templated_prompt", tmp_path, data={"powerlevel": 1}, force=True
    )
    assert conf.data["sentence"] == "It's only 1..."


def test_templated_prompt_builtins():
    data = query_user_data(
        {"question": {"default": "[[ now() ]]"}}, {}, {}, {}, False, envops
    )

    data = query_user_data(
        {"question": {"default": "[[ make_secret() ]]"}},
        {},
        {},
        {},
        False,
        envops,
    )
    assert isinstance(data["question"], str) and len(data["question"]) == 128


def test_templated_prompt_invalid():
    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"default": "[[ not_valid ]]"}},
        {},
        {},
        {},
        False,
        envops,
    )

    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"help": "[[ not_valid ]]"}}, {}, {}, {}, False, envops
    )

    with pytest.raises(InvalidTypeError):
        query_user_data(
            {"question": {"type": "[[ not_valid ]]"}},
            {},
            {},
            {},
            False,
            envops,
        )

    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"choices": ["[[ not_valid ]]"]}},
        {},
        {},
        {},
        False,
        envops,
    )

    # TODO: uncomment this later when EnvOps supports setting the undefined behavior
    # envops.undefined = StrictUndefined
    # with pytest.raises(UserMessageError):
    #     query_user_data(
    #         {"question": {"default": "[[ not_valid ]]"}}, {}, False, envops
    #     )
