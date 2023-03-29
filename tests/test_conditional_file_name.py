from plumbum import local
from plumbum.cmd import git
from pytest import TempPathFactory

import copier

from .helpers import build_file_tree


def test_render_conditional(tmp_path_factory: TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "{% if conditional %}file.txt{% endif %}.jinja"): (
                "This is {{ conditional.variable }}."
            ),
        }
    )
    copier.run_auto(str(src), dst, data={"conditional": {"variable": True}})
    assert (dst / "file.txt").read_text() == "This is True."


def test_dont_render_conditional(tmp_path_factory: TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "{% if conditional %}file.txt{% endif %}.jinja"): (
                "This is {{ conditional.variable }}."
            ),
        }
    )
    copier.run_auto(str(src), dst)
    assert not (dst / "file.txt").exists()


def test_render_conditional_subdir(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "subdir" / "{% if conditional %}file.txt{% endif %}.jinja"): (
                "This is {{ conditional.variable }}."
            ),
        }
    )
    copier.run_auto(str(src), dst, data={"conditional": {"variable": True}})
    assert (dst / "subdir" / "file.txt").read_text() == "This is True."


def test_dont_render_conditional_subdir(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "subdir" / "{% if conditional %}file.txt{% endif %}.jinja"): (
                "This is a {{ conditional.variable }}."
            ),
        }
    )
    copier.run_auto(str(src), dst)
    assert not (dst / "subdir" / "file.txt").exists()


def test_answer_changes(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    with local.cwd(src):
        build_file_tree(
            {
                "{{ _copier_conf.answers_file }}.jinja": "{{_copier_answers|to_nice_yaml}}",
                "copier.yml": """
                    condition:
                        type: bool
                """,
                "{% if condition %}file.txt{% endif %}.jinja": "",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-mv1")
        git("tag", "v1")

    copier.copy(str(src), dst, data={"condition": True})
    assert (dst / "file.txt").exists()

    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-mv1")

    copier.copy(dst_path=dst, data={"condition": False})
    assert not (dst / "file.txt").exists()
