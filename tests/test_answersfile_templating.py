from pathlib import Path

import pytest

import copier

from .helpers import build_file_tree


@pytest.fixture(scope="module")
def template_path(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root
            / ".copier-answers-{{module_name}}.yml": """\
                # Changes here will be overwritten by Copier
                [[ _copier_answers|to_nice_yaml ]]
                """,
            root
            / "copier.yml": """\
                _answers_file: .answers-file-changed-in-template.yml

                module_name:
                    type: str
                """,
        }
    )
    return str(root)


@pytest.mark.parametrize("answers_file", [None, ".changed-by-user.yaml"])
def test_answersfile_templating(template_path, tmp_path, answers_file):
    """Test copier behaves properly when using an answersfile."""
    copier.copy(
        template_path,
        tmp_path,
        {"module_name": "mymodule"},
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
    )
    answers_file = ".copier-answers-mymodule.yml"
    path = Path(tmp_path) / (answers_file)
    assert path.exists()
    copier.copy(
        template_path,
        tmp_path,
        {"module_name": "anothermodule"},
        defaults=True,
        overwrite=True,
    )
    answers_file = ".copier-answers-anothermodule.yml"
    path = Path(tmp_path) / (answers_file)
    assert path.exists()
    answers_file = ".copier-answers-mymodule.yml"
    path = Path(tmp_path) / (answers_file)
    assert path.exists()
