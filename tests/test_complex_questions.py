from pathlib import Path
from textwrap import dedent

from plumbum.cmd import copier as copier_cmd

from copier import copy

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_complex_questions"


def test_api(tmp_path):
    """Test copier correctly processes advanced questions and answers through API."""
    copy(
        SRC,
        tmp_path,
        {
            "love_me": False,
            "your_name": "LeChuck",
            "your_age": 220,
            "your_height": 1.9,
            "more_json_info": ["bad", "guy"],
            "anything_else": {"hates": "all"},
        },
        force=True,
    )
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        """
            love_me: false
            your_name: "LeChuck"
            your_age: 220
            your_height: 1.9
            more_json_info: ["bad", "guy"]
            anything_else: {"hates": "all"}
            choose_list: "first"
            choose_tuple: "second"
            choose_dict: "third"
            choose_number: null
            optional_value: null
        """
    )


def test_cli(tmp_path):
    """Test copier correctly processes advanced questions and answers through CLI."""
    (
        copier_cmd["copy", SRC, tmp_path]
        << dedent(
            # These are the answers; those marked as "wrong" will fail and
            # make the prompt function ask again
            """\
                y
                Guybrush Threpwood
                wrong your_age
                22
                wrong your_height
                1.56
                wrong more_json_info
                {"objective": "be a pirate"}
                {wrong anything_else
                ['Want some grog?', I'd love it]
                2
                3
                1
                1

            """
        )
    )(timeout=5)
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        r"""
            love_me: true
            your_name: "Guybrush Threpwood"
            your_age: 22
            your_height: 1.56
            more_json_info: {"objective": "be a pirate"}
            anything_else: ["Want some grog?", "I\u0027d love it"]
            choose_list: "second"
            choose_tuple: "third"
            choose_dict: "first"
            choose_number: -1.1
            optional_value: null
        """
    )


def test_api_str_data(tmp_path):
    """Test copier when all data comes as a string.

    This happens i.e. when using the --data CLI argument.
    """
    copy(
        SRC,
        tmp_path,
        data={
            "love_me": "false",
            "your_name": "LeChuck",
            "your_age": "220",
            "your_height": "1.9",
            "more_json_info": '["bad", "guy"]',
            "anything_else": "{'hates': 'all'}",
            "choose_number": "0",
        },
        force=True,
    )
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        r"""
            love_me: false
            your_name: "LeChuck"
            your_age: 220
            your_height: 1.9
            more_json_info: ["bad", "guy"]
            anything_else: {"hates": "all"}
            choose_list: "first"
            choose_tuple: "second"
            choose_dict: "third"
            choose_number: 0.0
            optional_value: null
        """
    )


def test_cli_with_flag_data_and_type_casts(tmp_path: Path):
    """Assert how choices work when copier is invoked with --data interactively."""
    (
        copier_cmd[
            "--data=choose_list=second",
            "--data=choose_dict=first",
            "--data=choose_tuple=third",
            "--data=choose_number=1",
            "copy",
            SRC,
            tmp_path,
        ]
        << dedent(
            # These are the answers; those marked as "wrong" will fail and
            # make the prompt function ask again
            """\
                y
                Guybrush Threpwood
                wrong your_age
                22
                wrong your_height
                1.56
                wrong more_json_info
                {"objective": "be a pirate"}
                {wrong anything_else
                ['Want some grog?', I'd love it]
            """
        )
    )(timeout=5)
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        r"""
            love_me: true
            your_name: "Guybrush Threpwood"
            your_age: 22
            your_height: 1.56
            more_json_info: {"objective": "be a pirate"}
            anything_else: ["Want some grog?", "I\u0027d love it"]
            choose_list: "second"
            choose_tuple: "third"
            choose_dict: "first"
            choose_number: 1.0
            optional_value: null
        """
    )
