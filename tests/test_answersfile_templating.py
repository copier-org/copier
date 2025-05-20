from __future__ import annotations

from pathlib import Path

import pytest

import copier
from copier._user_data import load_answersfile_data

from .helpers import build_file_tree


@pytest.fixture(scope="module")
def template_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            root / "copier.yml": """\
                _answers_file: ".copier-answers-{{ module_name }}.yml"

                module_name:
                    type: str
                """,
        }
    )
    return str(root)


@pytest.mark.parametrize("answers_file", [None, ".changed-by-user.yml"])
def test_answersfile_templating(
    template_path: str, tmp_path: Path, answers_file: str | None
) -> None:
    """
    Test copier behaves properly when _answers_file contains a template

    Checks that template is resolved successfully and that a subsequent
    copy that resolves to a different answers file doesn't clobber the
    old answers file.
    """
    copier.run_copy(
        template_path,
        tmp_path,
        {"module_name": "mymodule"},
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
        unsafe=True,
    )
    first_answers_file = (
        ".copier-answers-mymodule.yml"
        if answers_file is None
        else ".changed-by-user.yml"
    )
    assert (tmp_path / first_answers_file).exists()
    answers = load_answersfile_data(tmp_path, first_answers_file)
    assert answers["module_name"] == "mymodule"

    copier.run_copy(
        template_path,
        tmp_path,
        {"module_name": "anothermodule"},
        defaults=True,
        overwrite=True,
        unsafe=True,
    )

    # Assert second one created
    second_answers_file = ".copier-answers-anothermodule.yml"
    assert (tmp_path / second_answers_file).exists()
    answers = load_answersfile_data(tmp_path, second_answers_file)
    assert answers["module_name"] == "anothermodule"

    # Assert first one still exists
    assert (tmp_path / first_answers_file).exists()
    answers = load_answersfile_data(tmp_path, first_answers_file)
    assert answers["module_name"] == "mymodule"


def test_answersfile_templating_with_message_before_copy(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test templated `_answers_file` setting with `_message_before_copy`.

    Checks that the templated answers file name is rendered correctly while
    having printing a message before the "copy" operation, which uses the render
    context before including any answers from the questionnaire.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _answers_file: ".copier-answers-{{ module_name }}.yml"
                _message_before_copy: "Hello world"

                module_name:
                    type: str
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (src / "result.txt.jinja"): "{{ module_name }}",
        }
    )
    copier.run_copy(
        str(src), dst, data={"module_name": "mymodule"}, overwrite=True, unsafe=True
    )
    assert (dst / ".copier-answers-mymodule.yml").exists()
    answers = load_answersfile_data(dst, ".copier-answers-mymodule.yml")
    assert answers["module_name"] == "mymodule"
    assert (dst / "result.txt").exists()
    assert (dst / "result.txt").read_text() == "mymodule"


def test_answersfile_templating_phase(tmp_path_factory: pytest.TempPathFactory) -> None:
    """
    Ensure `_copier_phase` is available while render `answers_relpath`.
    Not because it is directly useful, but because some extensions might need it.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": """\
                _answers_file: ".copier-answers-{{ _copier_phase }}.yml"
                """,
            src / "{{ _copier_conf.answers_file }}.jinja": "",
        }
    )
    copier.run_copy(str(src), dst, overwrite=True, unsafe=True)
    assert (dst / ".copier-answers-render.yml").exists()
