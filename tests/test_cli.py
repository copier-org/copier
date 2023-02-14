import subprocess
import sys

import pytest
import yaml

from copier.cli import CopierApp

from .helpers import COPIER_CMD, build_file_tree


@pytest.fixture(scope="module")
def template_path(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root
            / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            root / "a.txt": "EXAMPLE_CONTENT",
        }
    )
    return str(root)


def test_good_cli_run(tmp_path, template_path):
    run_result = CopierApp.run(
        ["--quiet", "-a", "altered-answers.yml", str(template_path), str(tmp_path)],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "EXAMPLE_CONTENT"
    answers = yaml.safe_load((tmp_path / "altered-answers.yml").read_text())
    assert answers["_src_path"] == str(template_path)


def test_help():
    COPIER_CMD("--help-all")


def test_python_run():
    cmd = [sys.executable, "-m", "copier", "--help-all"]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_skip_filenotexists(tmp_path, template_path):
    run_result = CopierApp.run(
        [
            "--quiet",
            "-a",
            "altered-answers.yml",
            "--overwrite",
            "--skip=a.txt",
            str(template_path),
            str(tmp_path),
        ],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "EXAMPLE_CONTENT"
    answers = yaml.safe_load((tmp_path / "altered-answers.yml").read_text())
    assert answers["_src_path"] == str(template_path)


def test_skip_fileexists(tmp_path, template_path):
    a_txt = tmp_path / "a.txt"
    with open(a_txt, "w") as f_a:
        f_a.write("PREVIOUS_CONTENT")
    run_result = CopierApp.run(
        [
            "--quiet",
            "-a",
            "altered-answers.yml",
            "--overwrite",
            "--skip=a.txt",
            str(template_path),
            str(tmp_path),
        ],
        exit=False,
    )
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "PREVIOUS_CONTENT"
    answers = yaml.safe_load((tmp_path / "altered-answers.yml").read_text())
    assert answers["_src_path"] == str(template_path)
