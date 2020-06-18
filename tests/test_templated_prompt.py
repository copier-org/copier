import io
from collections import ChainMap
from datetime import datetime

import pytest

from copier.config.factory import filter_config, make_config
from copier.config.objects import EnvOps
from copier.config.user_data import InvalidTypeError, query_user_data
from copier.types import AnyByStrDict

answers_data: AnyByStrDict = {}
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
            ["(1) choice 1", "(2) copier", "Choice [1]"],
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
            ["(1) name 1", "(2) copier", "Choice [2]"],
        ),
        (
            {
                "templated_choices_mixed_list": {
                    "default": "value 2",
                    "choices": ["[[ main ]]", ["[[ main ]]", "value 2"]],
                },
            },
            "value 2",
            ["(1) copier", "(2) copier", "Choice [2]"],
        ),
    ],
)
def test_templated_prompt(
    questions_data, expected_value, expected_outputs, capsys, monkeypatch
):
    monkeypatch.setattr("sys.stdin", io.StringIO("\n\n"))
    questions_combined = filter_config({**main_question, **questions_data})[1]
    data = dict(
        ChainMap(
            query_user_data(questions_combined, {}, {}, True, envops),
            {k: v["default"] for k, v in questions_combined.items()},
        )
    )
    captured = capsys.readouterr()
    data.pop("main")
    name, value = list(data.items())[0]
    assert value == expected_value
    for output in expected_outputs:
        assert output in captured.out


def test_templated_prompt_custom_envops(dst):
    conf = make_config("./tests/demo_templated_prompt", dst, force=True)
    assert conf.data["sentence"] == "It's over 9000!"

    conf = make_config(
        "./tests/demo_templated_prompt", dst, data={"powerlevel": 1}, force=True
    )
    assert conf.data["sentence"] == "It's only 1..."


def test_templated_prompt_builtins():
    data = query_user_data(
        {"question": {"default": "[[ now() ]]"}}, answers_data, {}, False, envops
    )
    assert isinstance(data["question"], datetime)

    data = query_user_data(
        {"question": {"default": "[[ make_secret() ]]"}},
        answers_data,
        {},
        False,
        envops,
    )
    assert isinstance(data["question"], str) and len(data["question"]) == 128


def test_templated_prompt_invalid():
    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"default": "[[ not_valid ]]"}}, {}, answers_data, False, envops
    )

    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"help": "[[ not_valid ]]"}}, {}, answers_data, False, envops
    )

    with pytest.raises(InvalidTypeError):
        query_user_data(
            {"question": {"type": "[[ not_valid ]]"}}, {}, answers_data, False, envops
        )

    # assert no exception in non-strict mode
    query_user_data(
        {"question": {"choices": ["[[ not_valid ]]"]}}, {}, answers_data, False, envops
    )

    # TODO: uncomment this later when EnvOps supports setting the undefined behavior
    # envops.undefined = StrictUndefined
    # with pytest.raises(UserMessageError):
    #     query_user_data(
    #         {"question": {"default": "[[ not_valid ]]"}}, answers_data, False, envops
    #     )
