from pathlib import Path

import yaml

from copier.cli import CopierApp

from .helpers import COPIER_CMD

SIMPLE_DEMO_PATH = Path(__file__).parent / "demo_simple"


def test_good_cli_run(tmp_path):
    run_result = CopierApp.run(
        ["--quiet", "-a", "altered-answers.yml", str(SIMPLE_DEMO_PATH), str(tmp_path)],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text().strip() == "EXAMPLE_CONTENT"
    answers = yaml.safe_load((tmp_path / "altered-answers.yml").read_text())
    assert answers["_src_path"] == str(SIMPLE_DEMO_PATH)


def test_help():
    COPIER_CMD("--help-all")
