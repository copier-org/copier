import pytest

import copier

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree


@pytest.fixture(scope="module")
def demo_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo_tasks")
    build_file_tree(
        {
            root
            / "copier.yaml": f"""
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}

                other_file: bye

                # This tests two things:
                # 1. That the tasks are being executed in the destination folder; and
                # 2. That the tasks are being executed in order, one after another
                _tasks:
                    - mkdir hello
                    - cd hello && touch world
                    - touch [[ other_file ]]
                    - ["[[ _copier_python ]]", "-c", "open('pyfile', 'w').close()"]
            """
        }
    )
    return str(root)


def test_render_tasks(tmp_path, demo_template):
    copier.copy(demo_template, tmp_path, data={"other_file": "custom"})
    assert (tmp_path / "custom").is_file()


def test_copy_tasks(tmp_path, demo_template):
    copier.copy(demo_template, tmp_path, quiet=True, defaults=True, overwrite=True)
    assert (tmp_path / "hello").exists()
    assert (tmp_path / "hello").is_dir()
    assert (tmp_path / "hello" / "world").exists()
    assert (tmp_path / "bye").is_file()
    assert (tmp_path / "pyfile").is_file()


def test_pretend_mode(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = tmp_path_factory.mktemp("src"), tmp_path_factory.mktemp("dst")
    build_file_tree(
        {
            src
            / "copier.yml": """
                _tasks:
                    - touch created-by-task.txt
            """
        }
    )
    copier.copy(str(src), str(dst), pretend=True)
    assert not (dst / "created-by-task.txt").exists()
