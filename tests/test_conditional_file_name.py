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


def test_render_conditional_subdir(tmp_path_factory: TempPathFactory) -> None:
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


def test_dont_render_conditional_subdir(tmp_path_factory: TempPathFactory) -> None:
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
