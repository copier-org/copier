import json
from collections import deque
from pathlib import Path
from textwrap import dedent

import pexpect
import pytest

from copier import copy

from .helpers import (
    BRACKET_ENVOPS_JSON,
    COPIER_PATH,
    SUFFIX_TMPL,
    Keyboard,
    build_file_tree,
)


@pytest.fixture(scope="module")
def template_path(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root
            / "copier.yml": f"""\
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}
                love_me:
                    help: I need to know it. Do you love me?
                    type: bool
                your_name:
                    help: Please tell me your name.
                    type: str
                your_age:
                    help: How old are you?
                    type: int
                your_height:
                    help: What's your height?
                    type: float
                more_json_info:
                    multiline: true
                    type: json
                anything_else:
                    multiline: true
                    help: Wanna give me any more info?

                # In choices, the user will always write the choice index (1, 2, 3...)
                choose_list:
                    help: You see the value of the list items
                    default: first
                    choices:
                        - first
                        - second
                        - third
                choose_tuple:
                    help: You see the 1st tuple item, but I get the 2nd item as a result
                    default: second
                    choices:
                        - [one, first]
                        - [two, second]
                        - [three, third]
                choose_dict:
                    help: You see the dict key, but I get the dict value
                    default: third
                    choices:
                        one: first
                        two: second
                        three: third
                choose_number:
                    help: This must be a number
                    default: null
                    type: float
                    choices:
                        - -1.1
                        - 0
                        - 1

                # Simplified format is still supported
                minutes_under_water: 10
                optional_value: null
            """,
            root
            / "results.txt.tmpl": """\
                love_me: [[love_me|tojson]]
                your_name: [[your_name|tojson]]
                your_age: [[your_age|tojson]]
                your_height: [[your_height|tojson]]
                more_json_info: [[more_json_info|tojson]]
                anything_else: [[anything_else|tojson]]
                choose_list: [[choose_list|tojson]]
                choose_tuple: [[choose_tuple|tojson]]
                choose_dict: [[choose_dict|tojson]]
                choose_number: [[choose_number|tojson]]
                minutes_under_water: [[minutes_under_water|tojson]]
                optional_value: [[optional_value|tojson]]
            """,
        }
    )
    return str(root)


def test_api(tmp_path, template_path):
    """Test copier correctly processes advanced questions and answers through API."""
    copy(
        template_path,
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
        """\
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


def test_cli_interactive(tmp_path, spawn, template_path):
    """Test copier correctly processes advanced questions and answers through CLI."""
    invalid = [
        "Invalid value",
        "please try again",
    ]
    tui = spawn(COPIER_PATH + ("copy", template_path, str(tmp_path)), timeout=10)
    deque(
        map(
            tui.expect_exact,
            ["I need to know it. Do you love me?", "love_me", "Format: bool"],
        )
    )
    tui.send("y")
    deque(
        map(tui.expect_exact, ["Please tell me your name.", "your_name", "Format: str"])
    )
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
    deque(
        map(
            tui.expect_exact,
            [
                "You see the value of the list items",
                "choose_list",
                "Format: str",
                "first",
                "second",
                "third",
            ],
        )
    )
    tui.sendline()
    deque(
        map(
            tui.expect_exact,
            [
                "You see the 1st tuple item, but I get the 2nd item as a result",
                "choose_tuple",
                "one",
                "two",
                "three",
            ],
        )
    )
    tui.sendline()
    deque(
        map(
            tui.expect_exact,
            [
                "You see the dict key, but I get the dict value",
                "choose_dict",
                "one",
                "two",
                "three",
            ],
        )
    )
    tui.sendline()
    deque(
        map(
            tui.expect_exact,
            ["This must be a number", "choose_number", "-1.1", "0", "1"],
        )
    )
    tui.sendline()
    deque(map(tui.expect_exact, ["minutes_under_water", "Format: int", "10"]))
    tui.send(Keyboard.Backspace)
    tui.sendline()
    deque(map(tui.expect_exact, ["optional_value", "Format: yaml"]))
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        """\
            love_me: true
            your_name: "Guybrush Threpwood"
            your_age: 22
            your_height: 1.56
            more_json_info: {"objective": "be a pirate"}
            anything_else: ["Want some grog?", "I\\u0027d love it"]
            choose_list: "first"
            choose_tuple: "second"
            choose_dict: "third"
            choose_number: -1.1
            minutes_under_water: 1
            optional_value: null
        """
    )


def test_api_str_data(tmp_path, template_path):
    """Test copier when all data comes as a string.

    This happens i.e. when using the --data CLI argument.
    """
    copy(
        template_path,
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
        """\
            love_me: "false"
            your_name: "LeChuck"
            your_age: "220"
            your_height: "1.9"
            more_json_info: "[\\"bad\\", \\"guy\\"]"
            anything_else: "{\\u0027hates\\u0027: \\u0027all\\u0027}"
            choose_list: "first"
            choose_tuple: "second"
            choose_dict: "third"
            choose_number: "0"
            minutes_under_water: 10
            optional_value: null
        """
    )


def test_cli_interatively_with_flag_data_and_type_casts(
    tmp_path: Path, spawn, template_path
):
    """Assert how choices work when copier is invoked with --data interactively."""
    invalid = [
        "Invalid value",
        "please try again",
    ]
    tui = spawn(
        COPIER_PATH
        + (
            "--data=choose_list=second",
            "--data=choose_dict=first",
            "--data=choose_tuple=third",
            "--data=choose_number=1",
            "copy",
            template_path,
            str(tmp_path),
        ),
        timeout=10,
    )
    deque(
        map(
            tui.expect_exact,
            ["I need to know it. Do you love me?", "love_me", "Format: bool"],
        )
    )
    tui.send("y")
    deque(
        map(
            tui.expect_exact,
            ["Please tell me your name.", "your_name", "Format: str"],
        )
    )
    tui.sendline("Guybrush Threpwood")
    q = ["How old are you?", "your_age", "Format: int"]
    deque(map(tui.expect_exact, q))
    tui.sendline("wrong your_age")
    deque(map(tui.expect_exact, (invalid + q)))
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("22")
    q = ["What's your height?", "your_height", "Format: float"]
    deque(map(tui.expect_exact, (q)))
    tui.sendline("wrong your_height")
    deque(map(tui.expect_exact, (invalid + q)))
    tui.send((Keyboard.Alt + Keyboard.Backspace) * 2)
    tui.sendline("1.56")
    q = ["more_json_info", "Format: json"]
    deque(map(tui.expect_exact, (q)))
    tui.sendline('{"objective":')
    deque(map(tui.expect_exact, (invalid + q)))
    tui.sendline('"be a pirate"}')
    tui.send(Keyboard.Esc + Keyboard.Enter)
    q = ["Wanna give me any more info?", "anything_else", "Format: yaml"]
    deque(map(tui.expect_exact, (q)))
    tui.sendline("- Want some grog?")
    deque(map(tui.expect_exact, (invalid + q)))
    tui.sendline("- I'd love it")
    tui.send(Keyboard.Esc + Keyboard.Enter)
    deque(map(tui.expect_exact, ["minutes_under_water", "Format: int", "10"]))
    tui.sendline()
    deque(map(tui.expect_exact, ["optional_value", "Format: yaml"]))
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    results_file = tmp_path / "results.txt"
    assert results_file.read_text() == dedent(
        """\
            love_me: true
            your_name: "Guybrush Threpwood"
            your_age: 22
            your_height: 1.56
            more_json_info: {"objective": "be a pirate"}
            anything_else: ["Want some grog?", "I\\u0027d love it"]
            choose_list: "second"
            choose_tuple: "third"
            choose_dict: "first"
            choose_number: 1
            minutes_under_water: 10
            optional_value: null
        """
    )


def test_tui_inherited_default(tmp_path_factory, spawn):
    """Make sure a template inherits default as expected."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yaml": """\
                owner1:
                    type: str
                has_2_owners:
                    type: bool
                    default: false
                owner2:
                    type: str
                    default: "{{ owner1 }}"
                    when: "{{ has_2_owners }}"
            """,
            src / "answers.json.jinja": "{{ _copier_answers|to_nice_json }}",
        }
    )
    tui = spawn(
        COPIER_PATH + ("copy", str(src), str(dst)),
        timeout=10,
    )
    deque(map(tui.expect_exact, ["owner1?", "Format: str"]))
    tui.sendline("example")
    deque(map(tui.expect_exact, ["has_2_owners?", "Format: bool", "(y/N)"]))
    tui.send("y")
    deque(map(tui.expect_exact, ["owner2?", "Format: str", "example"]))
    tui.sendline("2")
    tui.expect_exact(pexpect.EOF)
    assert json.loads((dst / "answers.json").read_bytes()) == {
        "_src_path": str(src),
        "owner1": "example",
        "has_2_owners": True,
        "owner2": "example2",
    }


def test_selection_type_cast(tmp_path_factory, spawn):
    """Selection question with different types, properly casted."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yaml": """\
                postgres1: &pg
                    type: yaml
                    default: 10
                    help: Which PostgreSQL version do you want to deploy?
                    choices:
                        I will use an external PostgreSQL server: null
                        "9.6": 9.6
                        "10": 10
                postgres2: *pg
                postgres3: *pg
                nulls1: &nulls
                    type: yaml
                    choices:
                        - [same as key, null]
                        - [yaml-casted to a real null, "null"]
                        - [becomes array, "[one, 2, -3.0]"]
                nulls2: *nulls
                nulls3: *nulls
            """,
            src / "answers.json.jinja": "{{ _copier_answers|to_json }}",
        }
    )
    tui = spawn(
        COPIER_PATH + ("copy", str(src), str(dst)),
        timeout=10,
    )
    tui.expect_exact("Which PostgreSQL version do you want to deploy?")
    tui.expect_exact("postgres1?")
    tui.expect_exact("Format: yaml")
    tui.sendline(Keyboard.Down)
    tui.expect_exact("Which PostgreSQL version do you want to deploy?")
    tui.expect_exact("postgres2?")
    tui.expect_exact("Format: yaml")
    tui.sendline(Keyboard.Up)
    tui.expect_exact("Which PostgreSQL version do you want to deploy?")
    tui.expect_exact("postgres3?")
    tui.expect_exact("Format: yaml")
    tui.sendline()
    tui.expect_exact("nulls1?")
    tui.expect_exact("Format: yaml")
    tui.sendline()
    tui.expect_exact("nulls2?")
    tui.expect_exact("Format: yaml")
    tui.sendline(Keyboard.Down)
    tui.expect_exact("nulls3?")
    tui.expect_exact("Format: yaml")
    tui.sendline(Keyboard.Down + Keyboard.Down)
    tui.expect_exact(pexpect.EOF)
    assert json.loads((dst / "answers.json").read_bytes()) == {
        "_src_path": str(src),
        "nulls1": "same as key",
        "nulls2": None,
        "nulls3": ["one", 2, -3.0],
        "postgres1": "I will use an external PostgreSQL server",
        "postgres2": 9.6,
        "postgres3": 10,
    }
