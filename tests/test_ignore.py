"""Tests for the ``{% ignore %}`` tag that keeps developer-owned regions (#2184).

The tag renders its body on ``copier copy`` but is omitted from the renders
Copier produces internally during ``copier update``. Because the region is
absent from both the old and new template renders that feed the 3-way merge,
template changes inside it never reach the diff and the developer's own version
of the region survives, with no Copier syntax leaking into the rendered file.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from inline_snapshot import snapshot

from copier._main import run_copy, run_update

from .helpers import build_file_tree, git_save


@pytest.fixture
def template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A template with an ``{% ignore %}`` block in ``app.py.jinja``, at two tags.

    ``v2`` changes the surrounding code *and* the placeholder inside the block,
    so the tests can show that only the surroundings update.
    """
    src = tmp_path_factory.mktemp("src")
    v1 = dedent(
        """\
        CONFIG = "v1"


        def stable_helper():
            return 42


        {% ignore -%}
        def user_code():
            return "dummy v1"
        {%- endignore %}


        def another_stable():
            return "keep"
        """
    )
    v2 = (
        v1.replace('CONFIG = "v1"', 'CONFIG = "v2"')
        .replace('return "dummy v1"', 'return "dummy v2"')
        .replace('return "keep"', 'return "kept in v2"')
    )
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}\n"
            ),
            src / "app.py.jinja": v1,
        },
        dedent=False,
    )
    git_save(src, "v1", tag="v1")
    build_file_tree({src / "app.py.jinja": v2}, dedent=False)
    git_save(src, "v2", tag="v2")
    return src


def test_update_preserves_developer_region(
    template: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Developer content in an ``{% ignore %}`` block survives an update.

    The template changes the surrounding code *and* the placeholder inside the
    block; only the surroundings update while the developer's implementation is
    kept, with no merge conflict.
    """
    dst = tmp_path_factory.mktemp("dst")
    run_copy(str(template), dst, defaults=True, overwrite=True, vcs_ref="v1")

    app = dst / "app.py"
    assert app.read_text(encoding="utf-8") == snapshot("""\
CONFIG = "v1"


def stable_helper():
    return 42


def user_code():
    return "dummy v1"


def another_stable():
    return "keep"
""")
    git_save(dst, "generated")

    app.write_text(
        app.read_text(encoding="utf-8").replace(
            'return "dummy v1"', 'return "REAL IMPLEMENTATION"'
        ),
        encoding="utf-8",
    )
    git_save(dst, "customize")

    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    assert app.read_text(encoding="utf-8") == snapshot("""\
CONFIG = "v2"


def stable_helper():
    return 42


def user_code():
    return "REAL IMPLEMENTATION"


def another_stable():
    return "kept in v2"
""")


def test_update_without_customization_takes_template_default(
    template: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """If the developer never touched the block, they keep the v1 scaffolding.

    Because the block is omitted from the update renders, the template's newer
    placeholder does not overwrite the region -- it is developer-owned from the
    very first ``copy``.
    """
    dst = tmp_path_factory.mktemp("dst")
    run_copy(str(template), dst, defaults=True, overwrite=True, vcs_ref="v1")
    git_save(dst, "generated")

    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    assert (dst / "app.py").read_text(encoding="utf-8") == snapshot("""\
CONFIG = "v2"


def stable_helper():
    return 42


def user_code():
    return "dummy v1"


def another_stable():
    return "kept in v2"
""")
