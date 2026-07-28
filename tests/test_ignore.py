"""Tests for the ``{% ignore %}`` tag that keeps developer-owned regions (#2184).

The tag renders its body on ``copier copy`` but is omitted from the renders
Copier produces internally during ``copier update``. Because the region is
absent from both the old and new template renders that feed the 3-way merge,
template changes inside it never reach the diff and the developer's own version
of the region survives, with no Copier syntax leaking into the rendered file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2.sandbox import SandboxedEnvironment
from plumbum import local

from copier._jinja_ext import IgnoreExtension
from copier._main import run_copy, run_update

from .helpers import build_file_tree, git

# Unit tests for the extension in isolation.


@pytest.fixture
def env() -> SandboxedEnvironment:
    return SandboxedEnvironment(extensions=[IgnoreExtension])


def test_ignore_renders_body_outside_update(env: SandboxedEnvironment) -> None:
    template = env.from_string("a\n{% ignore %}b{% endignore %}\nc")
    assert template.render({"_copier_operation": "copy"}) == "a\nb\nc"


def test_ignore_omits_body_on_update(env: SandboxedEnvironment) -> None:
    template = env.from_string("a\n{% ignore %}b{% endignore %}\nc")
    assert template.render({"_copier_operation": "update"}) == "a\n\nc"


def test_ignore_trim_markers_clean_output(env: SandboxedEnvironment) -> None:
    """The idiomatic ``-%}``/``{%-`` markers strip the tag lines entirely."""
    template = env.from_string("a\n{% ignore -%}\nb\n{%- endignore %}\nc")
    assert template.render({"_copier_operation": "copy"}) == "a\nb\nc"
    assert template.render({"_copier_operation": "update"}) == "a\n\nc"


# End-to-end tests exercising the full copy + update flow.
# These also confirm the extension is registered by default (they use the tag
# with no ``_jinja_extensions`` configured).


def _commit_template(src: Path, body: str, tag: str) -> None:
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}\n"
            ),
            src / "app.py.jinja": body,
        },
        dedent=False,
    )
    with local.cwd(src):
        git("init") if not (src / ".git").exists() else None
        git("add", "-A")
        git("commit", "-m", tag)
        git("tag", tag)


_V1 = """\
import os
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

_V2 = (
    _V1.replace('CONFIG = "v1"', 'CONFIG = "v2"')
    .replace('return "dummy v1"', 'return "dummy v2"')
    .replace('return "keep"', 'return "kept in v2"')
)


def test_copy_renders_block_without_leaking_syntax(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Initial generation renders the block; no marker/tag survives."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    _commit_template(src, _V1, "v1")

    run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="v1")

    rendered = (dst / "app.py").read_text(encoding="utf-8")
    assert 'return "dummy v1"' in rendered  # scaffolding is present after copy
    assert "ignore" not in rendered  # no Copier syntax leaks into the file
    assert "{%" not in rendered and "%}" not in rendered


def test_update_preserves_developer_region(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Developer content in an ``{% ignore %}`` block survives an update.

    The template changes the surrounding code *and* the placeholder inside the
    block; only the surroundings update while the developer's implementation is
    kept, with no merge conflict.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    _commit_template(src, _V1, "v1")

    run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="v1")
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "generated")

    # Developer replaces the placeholder body with a real implementation.
    app = dst / "app.py"
    app.write_text(
        app.read_text(encoding="utf-8").replace(
            'return "dummy v1"', 'return "REAL IMPLEMENTATION"'
        ),
        encoding="utf-8",
    )
    with local.cwd(dst):
        git("commit", "-am", "customize")

    _commit_template(src, _V2, "v2")
    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    result = app.read_text(encoding="utf-8")
    assert "<<<<<<<" not in result  # clean merge
    assert 'return "REAL IMPLEMENTATION"' in result  # developer content kept
    assert 'return "dummy v2"' not in result  # template placeholder ignored
    assert 'CONFIG = "v2"' in result  # surrounding code updated
    assert 'return "kept in v2"' in result
    assert "ignore" not in result  # still no leaked syntax


def test_update_without_customization_takes_template_default(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """If the developer never touched the block, they keep the v1 scaffolding.

    Because the block is omitted from the update renders, the template's newer
    placeholder does not overwrite the region -- the region is developer-owned
    from the very first ``copy``.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    _commit_template(src, _V1, "v1")

    run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="v1")
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "generated")

    _commit_template(src, _V2, "v2")
    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    result = (dst / "app.py").read_text(encoding="utf-8")
    assert "<<<<<<<" not in result
    # The region keeps the originally generated content, not the v2 placeholder.
    assert 'return "dummy v1"' in result
    assert 'return "dummy v2"' not in result
    assert 'CONFIG = "v2"' in result  # surroundings still update
