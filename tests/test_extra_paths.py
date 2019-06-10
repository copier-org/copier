from pathlib import Path

from jinja2.exceptions import TemplateNotFound
import pytest

from .. import copier

CHILD_DIR = "./tests/demo_extra_paths/children"
CHILD_DIR_CONFIG = "./tests/demo_extra_paths/children_config"
PARENT_DIR = "./tests/demo_extra_paths/parent"


# def test_template_not_found(dst):
#     with pytest.raises(TemplateNotFound):
#         copier.copy(CHILD_DIR, dst)


# def test_parent_dir_not_found(dst):
#     with pytest.raises(ValueError):
#         copier.copy(CHILD_DIR, dst, extra_paths="foobar")


# def test_copy_with_extra_paths(dst):
#     copier.copy(CHILD_DIR, dst, extra_paths=[PARENT_DIR])

#     gen_file = dst / "child.txt"
#     result = gen_file.read_text()
#     print(result)
#     expected = Path(PARENT_DIR + "/parent.txt").read_text()
#     assert result == expected


def test_copy_with_extra_paths_from_config(dst):
    copier.copy(CHILD_DIR_CONFIG, dst)

    gen_file = dst / "child.txt"
    result = gen_file.read_text()
    print(result)
    expected = Path(PARENT_DIR + "/parent.txt").read_text()
    assert result == expected
