from pathlib import Path
from textwrap import dedent

import pexpect

from copier import copy

from .helpers import COPIER_PATH, PROJECT_TEMPLATE, Keyboard

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
            minutes_under_water: 10
            optional_value: null
        """
    )


def test_cli_interactive(tmp_path, spawn):
    """Test copier correctly processes advanced questions and answers through CLI."""
    invalid = [
        "Invalid value",
        "please try again",
    ]
    tui = spawn([COPIER_PATH, "copy", SRC, str(tmp_path)], timeout=10)
    tui.expect_exact(["I need to know it. Do you love me?", "love_me", "Format: bool"])
    tui.send("y")
    tui.expect_exact(["Please tell me your name.", "your_name", "Format: str"])
    tui.sendline("Guybrush Threpwood")
    q = ["How old are you?", "your_age", "Format: int"]
    tui.expect_exact(q)
    tui.sendline("wrong your_age")
    tui.expect_exact(invalid + q)
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("22")
    q = ["What's your height?", "your_height", "Format: float"]
    tui.expect_exact(q)
    tui.sendline("wrong your_height")
    tui.expect_exact(invalid + q)
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("1.56")
    q = ["more_json_info", "Format: json"]
    tui.expect_exact(q)
    tui.sendline('{"objective":')
    tui.expect_exact(invalid + q)
    tui.sendline('"be a pirate"}')
    tui.send(Keyboard.Esc + Keyboard.Enter)
    q = ["Wanna give me any more info?", "anything_else", "Format: yaml"]
    tui.expect_exact(q)
    tui.sendline("- Want some grog?")
    tui.expect_exact(invalid + q)
    tui.sendline("- I'd love it")
    tui.send(Keyboard.Esc + Keyboard.Enter)
    tui.expect_exact(
        [
            "You see the value of the list items",
            "choose_list",
            "Format: str",
            "first",
            "second",
            "third",
        ]
    )
    tui.sendline()
    tui.expect_exact(
        [
            "You see the 1st tuple item, but I get the 2nd item as a result",
            "choose_tuple",
            "one",
            "two",
            "three",
        ]
    )
    tui.sendline()
    tui.expect_exact(
        [
            "You see the dict key, but I get the dict value",
            "choose_dict",
            "one",
            "two",
            "three",
        ]
    )
    tui.sendline()
    tui.expect_exact(["This must be a number", "choose_number", "-1.1", "0", "1"])
    tui.sendline()
    tui.expect_exact(["minutes_under_water", "Format: int", "10"])
    tui.send(Keyboard.Backspace)
    tui.sendline()
    tui.expect_exact(["optional_value", "Format: yaml"])
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        r"""
            love_me: true
            your_name: "Guybrush Threpwood"
            your_age: 22
            your_height: 1.56
            more_json_info: {"objective": "be a pirate"}
            anything_else: ["Want some grog?", "I\u0027d love it"]
            choose_list: "first"
            choose_tuple: "second"
            choose_dict: "third"
            choose_number: -1.1
            minutes_under_water: 1
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
            minutes_under_water: 10
            optional_value: null
        """
    )


def test_cli_interatively_with_flag_data_and_type_casts(tmp_path: Path, spawn):
    """Assert how choices work when copier is invoked with --data interactively."""
    invalid = [
        "Invalid value",
        "please try again",
    ]
    tui = spawn(
        [
            COPIER_PATH,
            "--data=choose_list=second",
            "--data=choose_dict=first",
            "--data=choose_tuple=third",
            "--data=choose_number=1",
            "copy",
            SRC,
            str(tmp_path),
        ],
        timeout=10,
    )
    tui.expect_exact(["I need to know it. Do you love me?", "love_me", "Format: bool"])
    tui.send("y")
    tui.expect_exact(["Please tell me your name.", "your_name", "Format: str"])
    tui.sendline("Guybrush Threpwood")
    q = ["How old are you?", "your_age", "Format: int"]
    tui.expect_exact(q)
    tui.sendline("wrong your_age")
    tui.expect_exact(invalid + q)
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("22")
    q = ["What's your height?", "your_height", "Format: float"]
    tui.expect_exact(q)
    tui.sendline("wrong your_height")
    tui.expect_exact(invalid + q)
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("1.56")
    q = ["more_json_info", "Format: json"]
    tui.expect_exact(q)
    tui.sendline('{"objective":')
    tui.expect_exact(invalid + q)
    tui.sendline('"be a pirate"}')
    tui.send(Keyboard.Esc + Keyboard.Enter)
    q = ["Wanna give me any more info?", "anything_else", "Format: yaml"]
    tui.expect_exact(q)
    tui.sendline("- Want some grog?")
    tui.expect_exact(invalid + q)
    tui.sendline("- I'd love it")
    tui.send(Keyboard.Esc + Keyboard.Enter)
    tui.expect_exact(["minutes_under_water", "Format: int", "10"])
    tui.sendline()
    tui.expect_exact(["optional_value", "Format: yaml"])
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
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
            minutes_under_water: 10
            optional_value: null
        """
    )
