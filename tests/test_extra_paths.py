from pathlib import Path

import pytest
from jinja2.exceptions import TemplateNotFound

import copier

CHILD_DIR = "./tests/demo_extra_paths/children"
CHILD_DIR_CONFIG = "./tests/demo_extra_paths/children_config"
PARENT_DIR = "./tests/demo_extra_paths/parent"


def test_template_not_found(tmp_path):
    with pytest.raises(TemplateNotFound):
        copier.copy(CHILD_DIR, tmp_path)


def test_parent_dir_not_found(tmp_path):
    with pytest.raises(ValueError):
        copier.copy(CHILD_DIR, tmp_path, extra_paths="foobar")


def test_copy_with_extra_paths(tmp_path):
    copier.copy(CHILD_DIR, tmp_path, extra_paths=[PARENT_DIR])

    gen_file = tmp_path / "child.txt"
    result = gen_file.read_text()
    expected = Path(PARENT_DIR + "/parent.txt").read_text()
    assert result == expected


def test_copy_with_extra_paths_from_config(tmp_path):
    copier.copy(CHILD_DIR_CONFIG, tmp_path)

    gen_file = tmp_path / "child.txt"
    result = gen_file.read_text()
    expected = Path(PARENT_DIR + "/parent.txt").read_text()
    assert result == expected
