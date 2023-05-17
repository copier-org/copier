from pathlib import Path

import pytest
from plumbum import local

from copier import run_copy, run_recopy
from copier.cli import CopierApp

from .helpers import build_file_tree, git_save


@pytest.fixture(scope="module")
def tpl(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A simple template that supports updates."""
    dst = tmp_path_factory.mktemp("tpl")
    with local.cwd(dst):
        build_file_tree(
            {
                "copier.yml": "your_name: Mario",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
                "name.txt.jinja": "This is your name: {{ your_name }}.",
            }
        )
        git_save()
    return str(dst)


def test_recopy_discards_evolution_api(tpl: str, tmp_path: Path) -> None:
    # First copy
    run_copy(tpl, tmp_path, data={"your_name": "Luigi"}, defaults=True, overwrite=True)
    git_save(tmp_path)
    name_path = tmp_path / "name.txt"
    assert name_path.read_text() == "This is your name: Luigi."
    # Evolve subproject
    name_path.write_text("This is your name: Luigi. Welcome.")
    git_save(tmp_path)
    # Recopy
    run_recopy(tmp_path, defaults=True, overwrite=True)
    assert name_path.read_text() == "This is your name: Luigi."


def test_recopy_discards_evolution_cli(tpl: str, tmp_path: Path) -> None:
    # First copy
    run_copy(tpl, tmp_path, data={"your_name": "Peach"}, defaults=True, overwrite=True)
    git_save(tmp_path)
    name_path = tmp_path / "name.txt"
    assert name_path.read_text() == "This is your name: Peach."
    # Evolve subproject
    name_path.write_text("This is your name: Peach. Welcome.")
    git_save(tmp_path)
    # Recopy
    with local.cwd(tmp_path):
        _, retcode = CopierApp.run(["copier", "recopy", "-f"], exit=False)
    assert retcode == 0
    assert name_path.read_text() == "This is your name: Peach."
