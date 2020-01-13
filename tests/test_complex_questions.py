from textwrap import dedent

from plumbum.cmd import copier as copier_cmd

from copier import copy

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_complex_questions"


def test_api(dst):
    """Test copier processes fine advanced questions and answers through API."""
    copy(
        SRC,
        dst,
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
    results_file = dst / "results.txt"
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
            optional_value: null
        """
    )


def test_cli(dst):
    """Test copier processes fine advanced questions and answers through CLI."""
    (
        copier_cmd["copy", SRC, dst]
        << dedent(
            # These are the answers; those marked as "wrong" will fail and
            # make the prompt function ask again
            """
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

            """
        )
    )()
    results_file = dst / "results.txt"
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
            optional_value: null
        """
    )
