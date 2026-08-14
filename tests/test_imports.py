import re
from pathlib import Path

import pytest
import yaml

import copier
from copier._types import AnyByStrDict
from copier.errors import ForbiddenPathError

from .helpers import build_file_tree


@pytest.mark.parametrize(
    "subdir, settings",
    [
        (
            "",
            {
                "_exclude": ["includes"],
            },
        ),
        (
            "template",
            {
                "_subdirectory": "template",
            },
        ),
    ],
)
def test_include(
    tmp_path_factory: pytest.TempPathFactory, subdir: str, settings: AnyByStrDict
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): yaml.safe_dump(
                {
                    **settings,
                    "name": {
                        "type": "str",
                        "default": "The Name",
                    },
                    "slug": {
                        "type": "str",
                        "default": "{% include 'includes/name-slug.jinja' %}",
                    },
                }
            ),
            (src / "includes" / "name-slug.jinja"): (
                "{{ name|lower|replace(' ', '-') }}"
            ),
            # File for testing the Jinja include statement in `copier.yml`.
            (src / subdir / "slug-answer.txt.jinja"): "{{ slug }}",
            # File for testing the Jinja include statement as content.
            (src / subdir / "slug-from-include.txt.jinja"): (
                "{% include 'includes/name-slug.jinja' %}"
            ),
            # File for testing the Jinja include statement in the file name.
            (
                src
                / subdir
                / "{% include pathjoin('includes', 'name-slug.jinja') %}.txt"
            ): "",
            # File for testing the Jinja include statement in the folder name.
            (
                src
                / subdir
                / "{% include pathjoin('includes', 'name-slug.jinja') %}"
                / "test.txt"
            ): "",
        }
    )
    copier.run_copy(str(src), dst, defaults=True)
    assert (dst / "slug-answer.txt").read_text() == "the-name"
    assert (dst / "slug-from-include.txt").read_text() == "the-name"
    assert (dst / "the-name.txt").exists()
    assert (dst / "the-name" / "test.txt").exists()
    assert not (dst / "includes").exists()


@pytest.mark.parametrize("absolute", [False, True])
def test_include_resolves_symlink_outside_template_root_raises_error(
    tmp_path_factory: pytest.TempPathFactory, absolute: bool
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "template" / "copier.yml"): "_preserve_symlinks: true",
            (src / "template" / "symlink.txt"): (
                (src if absolute else Path("..")) / "outside" / "secrets.txt"
            ),
            (src / "template" / "stolen.txt.jinja"): "{% include 'symlink.txt' %}",
            (src / "outside" / "secrets.txt"): "s3cr3t",
        }
    )
    with pytest.raises(
        ForbiddenPathError,
        match=re.escape(f'{src / "outside" / "secrets.txt"}" is forbidden'),
    ):
        copier.run_copy(str(src / "template"), dst)


def test_include_resolves_symlink_inside_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_preserve_symlinks: true",
            (src / "inside.txt"): "inside",
            (src / "symlink.txt"): Path("inside.txt"),
            (src / "result.txt.jinja"): "{% include 'symlink.txt' %}",
        }
    )
    copier.run_copy(str(src), dst)
    assert (dst / "result.txt").read_text() == "inside"


@pytest.mark.parametrize(
    "subdir, settings",
    [
        (
            "",
            {
                "_exclude": ["includes"],
            },
        ),
        (
            "template",
            {
                "_subdirectory": "template",
            },
        ),
    ],
)
def test_import_macro(
    tmp_path_factory: pytest.TempPathFactory, subdir: str, settings: AnyByStrDict
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): yaml.safe_dump(
                {
                    **settings,
                    "name": {
                        "type": "str",
                        "default": "The Name",
                    },
                    "slug": {
                        "type": "str",
                        "default": (
                            "{% from 'includes/slugify.jinja' import slugify %}"
                            "{{ slugify(name) }}"
                        ),
                    },
                }
            ),
            (src / "includes" / "slugify.jinja"): (
                """\
                {% macro slugify(value) -%}
                {{ value|lower|replace(' ', '-') }}
                {%- endmacro %}
                """
            ),
            # File for testing the Jinja import statement in `copier.yml`.
            (src / subdir / "slug-answer.txt.jinja"): "{{ slug }}",
            # File for testing the Jinja import statement as content.
            (src / subdir / "slug-from-macro.txt.jinja"): (
                "{% from 'includes/slugify.jinja' import slugify %}{{ slugify(name) }}"
            ),
            # File for testing the Jinja import statement in the file name.
            (
                src
                / subdir
                / "{% from pathjoin('includes', 'slugify.jinja') import slugify %}{{ slugify(name) }}.txt"
            ): "",
            # File for testing the Jinja import statement in the folder name.
            (
                src
                / subdir
                / "{% from pathjoin('includes', 'slugify.jinja') import slugify %}{{ slugify(name) }}"
                / "test.txt"
            ): "",
        }
    )
    copier.run_copy(str(src), dst, defaults=True)
    assert (dst / "slug-answer.txt").read_text() == "the-name"
    assert (dst / "slug-from-macro.txt").read_text() == "the-name"
    assert (dst / "the-name.txt").exists()
    assert (dst / "the-name" / "test.txt").exists()
    assert not (dst / "includes").exists()
