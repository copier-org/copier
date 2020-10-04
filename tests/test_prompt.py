from pathlib import Path

import pexpect
import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

from .helpers import Keyboard, build_file_tree

DEFAULT = object()
MARIO_TREE = {
    "copier.yml": """\
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
def test_copy_default_advertised(tmp_path_factory, name):
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
        args = []
        if name is not DEFAULT:
            args.append(f"--data=your_name={name}")
        else:
            name = "Mario"  # Default in the template
        name = str(name)
        tui = pexpect.spawn(
            "copier", [str(template), ".", "--vcs-ref=v1"] + args, timeout=5
        )
        # Check what was captured
        tui.expect_exact(["in_love?", "Format: bool", "(Y/n)"])
        tui.sendline()
        tui.expect_exact(["Yes"])
        if not args:
            tui.expect_exact(
                ["If you have a name, tell me now.", "your_name?", "Format: str", name]
            )
            tui.sendline()
        tui.expect_exact(["Secret enemy name", "your_enemy?", "Format: str", "******"])
        tui.sendline()
        tui.expect_exact(["what_enemy_does?", "Format: str", f"Bowser hates {name}"])
        tui.sendline()
        tui.expect_exact(pexpect.EOF)
        assert "_commit: v1" in Path(".copier-answers.yml").read_text()
        # Update subproject
        git("init")
        git("add", ".")
        assert "_commit: v1" in Path(".copier-answers.yml").read_text()
        git("commit", "-m", "v1")
        tui = pexpect.spawn("copier", timeout=3)
        # Check what was captured
        tui.expect_exact(["in_love?", "Format: bool", "(Y/n)"])
        tui.sendline()
        tui.expect_exact(
            ["If you have a name, tell me now.", "your_name?", "Format: str", name]
        )
        tui.sendline()
        tui.expect_exact(["Secret enemy name", "your_enemy?", "Format: str", "Bowser"])
        tui.sendline()
        tui.expect_exact(["what_enemy_does?", "Format: str", f"Bowser hates {name}"])
        tui.sendline()
        tui.expect_exact(["Overwrite", ".copier-answers.yml", "[Y/n]"])
        tui.sendline()
        tui.expect_exact(pexpect.EOF)
        assert "_commit: v2" in Path(".copier-answers.yml").read_text()


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
        ("[[ question_1 ]]", True),
        ("[[ not question_1 ]]", False),
        ("[% if question_1 %]YES[% endif %]", True),
        ("[% if question_1 %]FALSE[% endif %]", False),
    ),
)
def test_when(tmp_path_factory, question_2_when, asks):
    """Test that the 2nd question is skipped or not, properly."""
    template, subproject = (
        tmp_path_factory.mktemp("template"),
        tmp_path_factory.mktemp("subproject"),
    )
    questions = {
        "question_1": {"type": "bool", "default": True},
        "question_2": {"default": "something", "when": question_2_when},
    }
    build_file_tree(
        {
            template / "copier.yml": yaml.dump(questions),
            template
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
        }
    )
    tui = pexpect.spawn("copier", [str(template), str(subproject)], timeout=5)
    tui.expect_exact(["question_1?", "Format: bool", "(Y/n)"])
    tui.sendline()
    if asks:
        tui.expect_exact(["question_2?", "Format: yaml"])
        tui.send(Keyboard.Alt + Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    answers = yaml.load((subproject / ".copier-answers.yml").read_text())
    assert answers == {
        "_src_path": str(template),
        "question_1": True,
        "question_2": "something",
    }
