from pytest import TempPathFactory

import copier
from tests.helpers import build_file_tree


def test_render_conditional(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "{% if conditional %}file.txt{% endif %}.jinja"
            : "This is {{ conditional.variable }}.",
        }
    )
    copier.run_auto(
        str(src),
        dst,
        data={"conditional": {"variable": True}},
    )

    file_rendered = (dst / "file.txt").read_text()
    file_expected = "This is True."
    assert file_rendered == file_expected


def test_dont_render_conditional(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "{% if conditional %}file.txt{% endif %}.jinja"
            : "This is {{ conditional.variable }}.",
        }
    )
    copier.run_auto(
        str(src),
        dst,
    )

    file_rendered = dst / "file.txt"
    assert not file_rendered.exists()


def test_render_conditional_subdir(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / 'subdir' / "{% if conditional %}file.txt{% endif %}.jinja"
            : "This is {{ conditional.variable }}.",
        }
    )
    copier.run_auto(
        str(src),
        dst,
        data={"conditional": {"variable": True}},
    )

    file_rendered = (dst / 'subdir' / "file.txt").read_text()
    file_expected = "This is True."
    assert file_rendered == file_expected


def test_dont_render_conditional_subdir(tmp_path_factory: TempPathFactory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "subdir" / "{% if conditional %}file.txt{% endif %}.jinja"
            : "This is a {{ conditional.variable }}.",
        }
    )
    copier.run_auto(
        str(src),
        dst,
    )

    file_rendered = dst / "subdir" / "file.txt"
    assert not file_rendered.exists()
