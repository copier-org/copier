from io import StringIO
from pathlib import Path

import pytest
from plumbum import local
from plumbum.cmd import git

from copier import copy

from .helpers import build_file_tree

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
        """,
    "[[ _copier_conf.answers_file ]].tmpl": "[[_copier_answers|to_nice_yaml]]",
}


@pytest.mark.timeout(5)
@pytest.mark.parametrize("name", [None, "Luigi"])
def test_copy_default_advertised(tmp_path_factory, monkeypatch, capsys, name):
    """Test that the questions for the user are OK"""
    monkeypatch.setattr("sys.stdin", StringIO("\n" * 3))
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
        copy(str(template), ".", vcs_ref="v1", data={"your_name": name})
        # Check what was captured
        captured = capsys.readouterr()
        assert "in_love? Format: bool\n🎤? [Y/n] " in captured.out
        assert (
            "Secret enemy name\nyour_enemy? Format: str\n🕵️ [Bowser]: " in captured.out
        )
        # We already sent the name through 'data', so it shouldn't be prompted
        assert "your_name" not in captured.out
        assert "_commit: v1" in Path(".copier-answers.yml").read_text()
        # Update subproject
        git("init")
        git("add", ".")
        git("commit", "-m", "v1")
        copy(dst_path=".")
        # Check what was captured
        captured = capsys.readouterr()
        assert (
            f"If you have a name, tell me now.\nyour_name? Format: str\n🎤 [{name}]: "
            in captured.out
        )
