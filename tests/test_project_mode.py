import warnings

import copier
from tests.helpers import build_file_tree


def test_render_items(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """
                _items: items
            """,
            src
            / "items"
            / "{{_item}}.txt.jinja": "This is {{ _item }}. Hello {{hello}}",
        }
    )
    # No warnings, because template is explicit
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_auto(
            str(src),
            dst,
            data={
                "items": ["one", "two", "three"],
                "hello": "world",
            },
            defaults=True,
            overwrite=True,
        )

        one_rendered = (dst / "one.txt").read_text()
        one_expected = "This is one. Hello world"
        assert one_rendered == one_expected

        one_rendered = (dst / "two.txt").read_text()
        one_expected = "This is two. Hello world"
        assert one_rendered == one_expected

        one_rendered = (dst / "three.txt").read_text()
        one_expected = "This is three. Hello world"
        assert one_rendered == one_expected


def test_render_items_conditional(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """
                _items: a
            """,
            src
            / "a"
            / "{{_item.value}}.txt.jinja": "This is {{ _item.value }}. Hello {{hello}}",
        }
    )
    # No warnings, because template is explicit
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        data = {
            "a": [
                {"value": "one"},
            ],
            "b": [
                {"value": "two"},
            ],
            "hello": "world",
        }
        copier.run_auto(str(src), dst, data=data, defaults=True, overwrite=True)

        one_rendered = (dst / "one.txt").read_text()
        one_expected = "This is one. Hello world"
        assert one_rendered == one_expected

        assert not (dst / "two.txt").exists()


def test_render_items_list(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """
                _items:
                - apples
                - oranges
            """,
            src
            / "apples"
            / "{{_item.value}}.txt.jinja": "This is {{ _item.value }}. Hello {{hello}}",
            src
            / "oranges"
            / "{{_item.value}}.txt.jinja": "This is {{ _item.value }}. Hello {{hello}}",
        }
    )
    # No warnings, because template is explicit
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        data = {
            "apples": [
                {"value": "apple_one"},
                {"value": "apple_two"},
            ],
            "oranges": [
                {"value": "orange_one"},
                {"value": "orange_two"},
            ],
            "hello": "world",
        }
        copier.run_auto(str(src), dst, data=data, defaults=True, overwrite=True)

        assert (dst / "apple_one.txt").read_text() == "This is apple_one. Hello world"
        assert (dst / "apple_two.txt").read_text() == "This is apple_two. Hello world"
        assert (dst / "orange_one.txt").read_text() == "This is orange_one. Hello world"
        assert (dst / "orange_one.txt").read_text() == "This is orange_one. Hello world"
