import pytest

import copier

from .helpers import build_file_tree


@pytest.fixture(scope="module")
def demo_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo_tasks")
    build_file_tree(
        {
            root
            / "copier.yaml": """
                other_file: bye

                # This tests two things:
                # 1. That the tasks are being executed in the destiantion folder; and
                # 2. That the tasks are being executed in order, one after another
                _tasks:
                    - mkdir hello
                    - cd hello && touch world
                    - touch [[ other_file ]]
            """
        }
    )
    return str(root)


def test_render_tasks(tmp_path, demo_template):
    copier.copy(demo_template, tmp_path, data={"other_file": "custom"})
    assert (tmp_path / "custom").is_file()


def test_copy_tasks(tmp_path, demo_template):
    copier.copy(demo_template, tmp_path, quiet=True, force=True)
    assert (tmp_path / "hello").exists()
    assert (tmp_path / "hello").is_dir()
    assert (tmp_path / "hello" / "world").exists()
    assert (tmp_path / "bye").is_file()
