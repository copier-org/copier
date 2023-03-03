from pathlib import Path

import pexpect
import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

from .helpers import (
    BRACKET_ENVOPS,
    BRACKET_ENVOPS_JSON,
    COPIER_PATH,
    SUFFIX_TMPL,
    Keyboard,
    build_file_tree,
    expect_prompt,
)

DEFAULT = object()
MARIO_TREE = {
    "copier.yml": f"""\
        _templates_suffix: {SUFFIX_TMPL}
        _envops: {BRACKET_ENVOPS_JSON}
        in_love:
            type: bool
            default: yes
        your_name:
            type: str
            default: Mario
            help: If you have a name, tell me now.
        your_enemy:
            type: str
            default: Bowser
            secret: yes
            help: Secret enemy name
        what_enemy_does:
            type: str
            default: "[[ your_enemy ]] hates [[ your_name ]]"
        """,
    "[[ _copier_conf.answers_file ]].tmpl": "[[_copier_answers|to_nice_yaml]]",
}


@pytest.mark.parametrize("name", [DEFAULT, None, "Luigi"])
def test_copy_default_advertised(tmp_path_factory, spawn, name):
    """Test that the questions for the user are OK"""
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    with local.cwd(template):
        build_file_tree(MARIO_TREE)
        git("init")
        git("add", ".")
        git("commit", "-m", "v1")
        git("tag", "v1")
        git("commit", "--allow-empty", "-m", "v2")
        git("tag", "v2")
    with local.cwd(subproject):
        # Copy the v1 template
        args = ()
        if name is not DEFAULT:
            args += (f"--data=your_name={name}",)
        else:
            name = "Mario"  # Default in the template
        name = str(name)
        tui = spawn(
            COPIER_PATH + (str(template), ".", "--vcs-ref=v1") + args, timeout=10
        )
        # Check what was captured
        expect_prompt(tui, "in_love", "bool")
        tui.expect_exact("(Y/n)")
        tui.sendline()
        tui.expect_exact("Yes")
        if not args:
            expect_prompt(
                tui, "your_name", "str", help="If you have a name, tell me now."
            )
            tui.expect_exact(name)
            tui.sendline()
        expect_prompt(tui, "your_enemy", "str", help="Secret enemy name")
        tui.expect_exact("******")
        tui.sendline()
        expect_prompt(tui, "what_enemy_does", "str")
        tui.expect_exact(f"Bowser hates {name}")
        tui.sendline()
        tui.expect_exact(pexpect.EOF)
        assert "_commit: v1" in Path(".copier-answers.yml").read_text()
        # Update subproject
        git("init")
        git("add", ".")
        assert "_commit: v1" in Path(".copier-answers.yml").read_text()
        git("commit", "-m", "v1")
        tui = spawn(COPIER_PATH, timeout=30)
        # Check what was captured
        expect_prompt(tui, "in_love", "bool")
        tui.expect_exact("(Y/n)")
        tui.sendline()
        expect_prompt(tui, "your_name", "str", help="If you have a name, tell me now.")
        tui.expect_exact(name)
        tui.sendline()
        expect_prompt(tui, "your_enemy", "str", help="Secret enemy name")
        tui.expect_exact("******")
        tui.sendline()
        expect_prompt(tui, "what_enemy_does", "str")
        tui.expect_exact(f"Bowser hates {name}")
        tui.sendline()
        tui.expect_exact(pexpect.EOF)
        assert "_commit: v2" in Path(".copier-answers.yml").read_text()


@pytest.mark.parametrize(
    "question_1",
    # All these values evaluate to true
    (
        True,
        1,
        1.1,
        -1,
        -0.001,
        "1",
        "1.1",
        "1st",
        "-1",
        "0.1",
        "00001",
        "000.0001",
        "-0001",
        "-000.001",
        "+001",
        "+000.001",
        "hello! 🤗",
    ),
)
@pytest.mark.parametrize(
    "question_2_when, asks",
    (
        (True, True),
        (False, False),
        ("trUe", True),
        ("faLse", False),
        ("Yes", True),
        ("nO", False),
        ("Y", True),
        ("N", False),
        ("on", True),
        ("off", False),
        ("~", False),
        ("NonE", False),
        ("nulL", False),
        ("[[ question_1 ]]", True),
        ("[[ not question_1 ]]", False),
        ("[% if question_1 %]YES[% endif %]", True),
        ("[% if question_1 %]FALSE[% endif %]", False),
    ),
)
def test_when(tmp_path_factory, question_1, question_2_when, spawn, asks):
    """Test that the 2nd question is skipped or not, properly."""
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    questions = {
        "_envops": BRACKET_ENVOPS,
        "_templates_suffix": SUFFIX_TMPL,
        "question_1": question_1,
        "question_2": {"default": "something", "type": "yaml", "when": question_2_when},
    }
    build_file_tree(
        {
            template / "copier.yml": yaml.dump(questions),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question_1", type(question_1).__name__)
    tui.sendline()
    if asks:
        expect_prompt(tui, "question_2", "yaml")
        tui.sendline()
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers == {
        "_src_path": str(template),
        "question_1": question_1,
        "question_2": "something",
    }


def test_placeholder(tmp_path_factory, spawn):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.dump(
                {
                    "_envops": BRACKET_ENVOPS,
                    "_templates_suffix": SUFFIX_TMPL,
                    "question_1": "answer 1",
                    "question_2": {
                        "type": "str",
                        "help": "write a list of answers",
                        "placeholder": "Write something like [[ question_1 ]], but better",
                    },
                }
            ),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question_1", "str")
    tui.expect_exact("answer 1")
    tui.sendline()
    expect_prompt(tui, "question_2", "str", help="write a list of answers")
    tui.expect_exact("Write something like answer 1, but better")
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers == {
        "_src_path": str(template),
        "question_1": "answer 1",
        "question_2": "",
    }


@pytest.mark.parametrize("type_", ("str", "yaml", "json"))
def test_multiline(tmp_path_factory, spawn, type_):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.dump(
                {
                    "_envops": BRACKET_ENVOPS,
                    "_templates_suffix": SUFFIX_TMPL,
                    "question_1": "answer 1",
                    "question_2": {"type": type_},
                    "question_3": {"type": type_, "multiline": True},
                    "question_4": {
                        "type": type_,
                        "multiline": "[[ question_1 == 'answer 1' ]]",
                    },
                    "question_5": {
                        "type": type_,
                        "multiline": "[[ question_1 != 'answer 1' ]]",
                    },
                }
            ),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question_1", "str")
    tui.expect_exact("answer 1")
    tui.sendline()
    expect_prompt(tui, "question_2", type_)
    tui.sendline('"answer 2"')
    expect_prompt(tui, "question_3", type_)
    tui.sendline('"answer 3"')
    tui.send(Keyboard.Alt + Keyboard.Enter)
    expect_prompt(tui, "question_4", type_)
    tui.sendline('"answer 4"')
    tui.send(Keyboard.Alt + Keyboard.Enter)
    expect_prompt(tui, "question_5", type_)
    tui.sendline('"answer 5"')
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    if type_ == "str":
        assert answers == {
            "_src_path": str(template),
            "question_1": "answer 1",
            "question_2": '"answer 2"',
            "question_3": ('"answer 3"\n'),
            "question_4": ('"answer 4"\n'),
            "question_5": ('"answer 5"'),
        }
    else:
        assert answers == {
            "_src_path": str(template),
            "question_1": "answer 1",
            "question_2": ("answer 2"),
            "question_3": ("answer 3"),
            "question_4": ("answer 4"),
            "question_5": ("answer 5"),
        }


@pytest.mark.parametrize(
    "choices",
    (
        [1, 2, 3],
        [["one", 1], ["two", 2], ["three", 3]],
        {"one": 1, "two": 2, "three": 3},
    ),
)
def test_update_choice(tmp_path_factory, spawn, choices):
    """Choices are properly remembered and selected in TUI when updating."""
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    # Create template
    build_file_tree(
        {
            template
            / "copier.yml": f"""
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}
                pick_one:
                    type: float
                    default: 3
                    choices: {choices}
                """,
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    with local.cwd(template):
        git("init")
        git("add", ".")
        git("commit", "-m one")
        git("tag", "v1")
    # Copy
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "pick_one", "float")
    tui.sendline(Keyboard.Up)
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers["pick_one"] == 2.0
    with local.cwd(subproject):
        git("init")
        git("add", ".")
        git("commit", "-m1")
    # Update
    tui = spawn(COPIER_PATH + (str(subproject),), timeout=10)
    expect_prompt(tui, "pick_one", "float")
    tui.sendline(Keyboard.Down)
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers["pick_one"] == 3.0


@pytest.mark.skip("TODO: fix this")
def test_multiline_defaults(tmp_path_factory, spawn):
    """Multiline questions with scalar defaults produce multiline defaults."""
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    # Create template
    build_file_tree(
        {
            template
            / "copier.yaml": """
                yaml_single:
                    type: yaml
                    default: &default
                        - one
                        - two
                        - three:
                            - four
                yaml_multi:
                    type: yaml
                    multiline: "{{ 'me' == ('m' + 'e') }}"
                    default: *default
                json_single:
                    type: json
                    default: *default
                json_multi:
                    type: json
                    multiline: yes
                    default: *default
                """,
            template
            / "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
        }
    )
    # Copy
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "yaml_single", "yaml")
    # This test will always fail here, because python prompt toolkit gives
    # syntax highlighting to YAML and JSON outputs, encoded into terminal
    # colors and all that stuff.
    # TODO Fix this test some day.
    tui.expect_exact("[one, two, {three: [four]}]")
    tui.send(Keyboard.Enter)
    expect_prompt(tui, "yaml_multi", "yaml")
    tui.expect_exact("> - one\n  - two\n  - three:\n    - four")
    tui.send(Keyboard.Alt + Keyboard.Enter)
    expect_prompt(tui, "json_single", "json")
    tui.expect_exact('["one", "two", {"three": ["four"]}]')
    tui.send(Keyboard.Enter)
    expect_prompt(tui, "json_multi", "json")
    tui.expect_exact(
        '> [\n    "one",\n    "two",\n    {\n      "three": [\n        "four"\n      ]\n    }\n  ]'
    )
    tui.send(Keyboard.Alt + Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert (
        answers["yaml_single"]
        == answers["yaml_multi"]
        == answers["json_single"]
        == answers["json_multi"]
        == ["one", "two", {"three": ["four"]}]
    )


def test_partial_interrupt(tmp_path_factory, spawn):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.safe_dump(
                {
                    "question_1": "answer 1",
                    "question_2": "answer 2",
                }
            ),
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question_1", "str")
    tui.expect_exact("answer 1")
    # Answer the first question using the default.
    tui.sendline()
    # Send a ctrl-c.
    tui.send(Keyboard.ControlC + Keyboard.Enter)
    # This string (or similar) should show in the output if we've gracefully caught the
    # interrupt.
    # We won't want our custom exception (CopierAnswersInterrupt) propagating
    # to an uncaught stacktrace.
    tui.expect_exact("Execution stopped by user\n")
    tui.expect_exact(pexpect.EOF)


def test_var_name_value_allowed(tmp_path_factory, spawn):
    """Test that a question var name "value" causes no name collision.

    See https://github.com/copier-org/copier/pull/780 for more details.
    """
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    # Create template
    build_file_tree(
        {
            template
            / "copier.yaml": """
                value:
                    type: str
                    default: string
                """,
            template
            / "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
        }
    )
    # Copy
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "value", "str")
    tui.expect_exact("string")
    tui.send(Keyboard.Alt + Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    # Check answers file
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers["value"] == "string"


@pytest.mark.parametrize(
    "type_name, expected_answer",
    [
        ("str", ""),
        ("int", ValueError("Invalid input")),
        ("float", ValueError("Invalid input")),
        ("json", ValueError("Invalid input")),
        ("yaml", None),
    ],
)
def test_required_text_question(tmp_path_factory, spawn, type_name, expected_answer):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.dump(
                {
                    "_envops": BRACKET_ENVOPS,
                    "_templates_suffix": SUFFIX_TMPL,
                    "question": {"type": type_name},
                }
            ),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question", type_name)
    tui.expect_exact("")
    tui.sendline()
    if isinstance(expected_answer, ValueError):
        tui.expect_exact(str(expected_answer))
        assert not (subproject / ".copier-answers.yml").exists()
    else:
        tui.expect_exact(pexpect.EOF)
        answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
        assert answers == {
            "_src_path": str(template),
            "question": expected_answer,
        }


def test_required_bool_question(tmp_path_factory, spawn):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.dump(
                {
                    "_envops": BRACKET_ENVOPS,
                    "_templates_suffix": SUFFIX_TMPL,
                    "question": {"type": "bool"},
                }
            ),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question", "bool")
    tui.expect_exact("(y/N)")
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers == {
        "_src_path": str(template),
        "question": False,
    }


@pytest.mark.parametrize(
    "type_name, choices, expected_answer",
    [
        ("str", ["one", "two", "three"], "one"),
        ("int", [1, 2, 3], 1),
        ("float", [1.0, 2.0, 3.0], 1.0),
        ("json", ["[1]", "[2]", "[3]"], [1]),
        ("yaml", ["- 1", "- 2", "- 3"], [1]),
    ],
)
def test_required_choice_question(
    tmp_path_factory, spawn, type_name, choices, expected_answer
):
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    build_file_tree(
        {
            template
            / "copier.yml": yaml.dump(
                {
                    "_envops": BRACKET_ENVOPS,
                    "_templates_suffix": SUFFIX_TMPL,
                    "question": {
                        "type": type_name,
                        "choices": choices,
                    },
                }
            ),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = spawn(COPIER_PATH + (str(template), str(subproject)), timeout=10)
    expect_prompt(tui, "question", type_name)
    tui.sendline()
    tui.expect_exact(pexpect.EOF)
    answers = yaml.safe_load((subproject / ".copier-answers.yml").read_text())
    assert answers == {
        "_src_path": str(template),
        "question": expected_answer,
    }
