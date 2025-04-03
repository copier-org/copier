from pathlib import Path
from textwrap import dedent

import pytest
from plumbum import local

from copier import run_copy, run_recopy
from copier._cli import CopierApp
from copier._user_data import load_answersfile_data
from copier._vcs import get_git

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


def test_recopy_works_without_replay(tpl: str, tmp_path: Path) -> None:
    # First copy
    run_copy(tpl, tmp_path, defaults=True, overwrite=True)
    git_save(tmp_path)
    assert (tmp_path / "name.txt").read_text() == "This is your name: Mario."
    # Modify template altering git history
    Path(tpl, "name.txt.jinja").write_text("This is my name: {{ your_name }}.")
    tpl_git = get_git(tpl)
    tpl_git("commit", "-a", "--amend", "--no-edit")
    # Make sure old dangling commit is lost
    # DOCS https://stackoverflow.com/a/63209363/1468388
    tpl_git("reflog", "expire", "--expire=now", "--all")
    tpl_git("gc", "--prune=now", "--aggressive")
    # Recopy
    run_recopy(tmp_path, skip_answered=True, overwrite=True)
    assert (tmp_path / "name.txt").read_text() == "This is my name: Mario."


def test_recopy_with_skip_answered_and_new_answer(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "boolean: false",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
        }
    )
    git_save(src)
    # First copy
    run_copy(str(src), dst, defaults=True, overwrite=True)
    git_save(dst)
    answers = load_answersfile_data(dst)
    assert answers["boolean"] is False
    # Recopy with different answer and `skip_answered=True`
    run_recopy(dst, data={"boolean": "true"}, skip_answered=True, overwrite=True)
    answers = load_answersfile_data(dst)
    assert answers["boolean"] is True


def test_recopy_dont_validate_computed_value(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": dedent(
                """\
                computed:
                    type: str
                    default: foo
                    when: false
                    validator: "This validator should never be rendered"
                """
            ),
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
        }
    )
    git_save(src)
    # First copy
    run_copy(str(src), dst, defaults=True, overwrite=True)
    git_save(dst)
    answers = load_answersfile_data(dst)
    assert "computed" not in answers
    # Recopy
    run_recopy(dst, overwrite=True)
    answers = load_answersfile_data(dst)
    assert "computed" not in answers


def test_conditional_computed_value(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            src / "copier.yml": (
                """\
                first:
                    type: bool

                second:
                    type: bool
                    default: "{{ first }}"
                    when: "{{ first }}"
                """
            ),
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "log.txt.jinja": "{{ first }} {{ second }}",
        }
    )
    git_save(src)

    run_copy(str(src), dst, data={"first": True}, defaults=True)
    answers = load_answersfile_data(dst)
    assert answers["first"] is True
    assert answers["second"] is True
    assert (dst / "log.txt").read_text() == "True True"

    git_save(dst, "v1")

    run_recopy(dst, data={"first": False}, overwrite=True)
    answers = load_answersfile_data(dst)
    assert answers["first"] is False
    assert "second" not in answers
    assert (dst / "log.txt").read_text() == "False False"

    git_save(dst, "v2")

    run_recopy(dst, data={"first": True}, defaults=True, overwrite=True)
    answers = load_answersfile_data(dst)
    assert answers["first"] is True
    assert answers["second"] is True
    assert (dst / "log.txt").read_text() == "True True"
