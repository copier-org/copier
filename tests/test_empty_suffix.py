import pytest

import copier

from .helpers import build_file_tree


def test_empty_suffix(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                _templates_suffix: ""
                name:
                    type: str
                    default: pingu
                """
            ),
            (src / "render_me"): "Hello {{name}}!",
            (src / "{{name}}.txt"): "Hello {{name}}!",
            (src / "{{name}}" / "render_me.txt"): "Hello {{name}}!",
        }
    )
    copier.copy(str(src), dst, defaults=True, overwrite=True)

    assert not (dst / "copier.yaml").exists()

    assert (dst / "render_me").exists()
    assert (dst / "pingu.txt").exists()
    assert (dst / "pingu" / "render_me.txt").exists()

    expected = "Hello pingu!"
    assert (dst / "render_me").read_text() == expected
    assert (dst / "pingu.txt").read_text() == expected
    assert (dst / "pingu" / "render_me.txt").read_text() == expected


def test_binary_file_fallback_to_copy(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                _templates_suffix: ""
                name:
                    type: str
                    default: pingu
                """
            ),
            (src / "logo.png"): (
                b"\x89PNG\r\n\x1a\n\x00\rIHDR\x00\xec\n{{name}}\n\x00\xec"
            ),
        }
    )
    copier.copy(str(src), dst, defaults=True, overwrite=True)
    logo = dst / "logo.png"
    assert logo.exists()
    logo_bytes = logo.read_bytes()
    assert b"{{name}}" in logo_bytes
    assert b"pingu" not in logo_bytes
