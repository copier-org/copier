import copier

from .helpers import build_file_tree


def test_empty_suffix(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo_empty_suffix")
    build_file_tree(
        {
            root
            / "copier.yaml": """
                _templates_suffix: ""
                name:
                    type: str
                    default: pingu
            """,
            root / "render_me": "Hello {{name}}!",
            root / "{{name}}.txt": "Hello {{name}}!",
            root / "{{name}}" / "render_me.txt": "Hello {{name}}!",
        }
    )
    dest = tmp_path_factory.mktemp("dst")
    copier.copy(str(root), dest, defaults=True, overwrite=True)

    assert not (dest / "copier.yaml").exists()

    assert (dest / "render_me").exists()
    assert (dest / "pingu.txt").exists()
    assert (dest / "pingu" / "render_me.txt").exists()

    expected = "Hello pingu!"
    assert (dest / "render_me").read_text() == expected
    assert (dest / "pingu.txt").read_text() == expected
    assert (dest / "pingu" / "render_me.txt").read_text() == expected
