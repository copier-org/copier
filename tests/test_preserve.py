"""Tests for preserving developer-owned regions across ``copier update`` (#2184)."""

from __future__ import annotations

from pathlib import Path

import pytest
from plumbum import local

from copier._main import run_copy, run_update
from copier._preserve import (
    PRESERVE_END_TOKEN,
    PRESERVE_START_TOKEN,
    PreserveMarkerError,
    _apply_regions,
    _parse_regions,
    _RegionKey,
    capture_preserved_regions,
    find_marker_files,
    restore_preserved_regions,
)

from .helpers import build_file_tree, git

# Unit tests for the parsing / capture / restore primitives.


def test_parse_regions_named_and_anonymous() -> None:
    text = (
        f"head\n# {PRESERVE_START_TOKEN} foo\nA\nB\n# {PRESERVE_END_TOKEN} foo\n"
        f"mid\n# {PRESERVE_START_TOKEN}\nC\n# {PRESERVE_END_TOKEN}\ntail\n"
    )
    regions = _parse_regions(text)
    assert [r.identifier for r in regions] == ["foo", None]
    assert regions[0].body == "A\nB\n"
    assert regions[1].body == "C\n"


def test_parse_regions_empty_body() -> None:
    text = f"# {PRESERVE_START_TOKEN} x\n# {PRESERVE_END_TOKEN} x\n"
    (region,) = _parse_regions(text)
    assert region.body == ""


@pytest.mark.parametrize(
    "text",
    [
        f"# {PRESERVE_START_TOKEN}\nno close\n",
        f"# {PRESERVE_END_TOKEN}\n",
        f"# {PRESERVE_START_TOKEN}\n# {PRESERVE_START_TOKEN}\n# {PRESERVE_END_TOKEN}\n",
    ],
)
def test_parse_regions_malformed(text: str) -> None:
    with pytest.raises(PreserveMarkerError):
        _parse_regions(text)


def test_apply_regions_replaces_only_matching_bodies() -> None:
    original = (
        f"# {PRESERVE_START_TOKEN} keep\nUSER\n# {PRESERVE_END_TOKEN} keep\n"
        f"# {PRESERVE_START_TOKEN} other\nOTHER-USER\n# {PRESERVE_END_TOKEN} other\n"
    )
    captured: dict[_RegionKey, str] = {
        key: region.body
        for key, region in zip(("keep", "other"), _parse_regions(original), strict=True)
    }
    # A new render where both bodies were changed by the template.
    new_render = (
        "new header\n"
        f"# {PRESERVE_START_TOKEN} keep\nTEMPLATE\n# {PRESERVE_END_TOKEN} keep\n"
        f"# {PRESERVE_START_TOKEN} other\nTEMPLATE2\n# {PRESERVE_END_TOKEN} other\n"
    )
    result = _apply_regions(new_render, captured)
    assert "USER" in result
    assert "OTHER-USER" in result
    assert "TEMPLATE" not in result
    assert result.startswith("new header\n")  # surrounding content kept from render


def test_apply_regions_keeps_updated_marker_lines() -> None:
    captured: dict[_RegionKey, str] = {"x": "USER\n"}
    # Template moved the region and changed the marker's comment style.
    new_render = f"// {PRESERVE_START_TOKEN} x\nTEMPLATE\n// {PRESERVE_END_TOKEN} x\n"
    result = _apply_regions(new_render, captured)
    assert result == f"// {PRESERVE_START_TOKEN} x\nUSER\n// {PRESERVE_END_TOKEN} x\n"


def test_apply_regions_ignores_new_region() -> None:
    captured: dict[_RegionKey, str] = {}  # nothing captured
    new_render = (
        f"# {PRESERVE_START_TOKEN} fresh\nDUMMY\n# {PRESERVE_END_TOKEN} fresh\n"
    )
    assert _apply_regions(new_render, captured) == new_render


def test_capture_and_restore_roundtrip(tmp_path: Path) -> None:
    project = tmp_path / "project"
    render = tmp_path / "render"
    build_file_tree(
        {
            project / "a.py": (
                f"top\n# {PRESERVE_START_TOKEN} g\nMINE\n# {PRESERVE_END_TOKEN} g\nbot\n"
            ),
            project / "plain.txt": "no markers here",
            render / "a.py": (
                f"TOP2\n# {PRESERVE_START_TOKEN} g\nDUMMY\n# {PRESERVE_END_TOKEN} g\nBOT2\n"
            ),
        }
    )
    captured = capture_preserved_regions(project)
    assert set(captured) == {Path("a.py")}
    restore_preserved_regions(render, captured)
    restored = (render / "a.py").read_text(encoding="utf-8")
    assert "MINE" in restored and "DUMMY" not in restored
    # Surrounding template content in the render is untouched.
    assert restored.startswith("TOP2\n") and restored.endswith("BOT2\n")


def test_capture_skips_binary_and_malformed(tmp_path: Path) -> None:
    build_file_tree(
        {
            tmp_path / "binary.bin": b"\x00\x01\x02" + PRESERVE_START_TOKEN.encode(),
            tmp_path / "bad.py": f"# {PRESERVE_START_TOKEN}\nunclosed\n",
        }
    )
    assert capture_preserved_regions(tmp_path) == {}


def test_find_marker_files(tmp_path: Path) -> None:
    build_file_tree(
        {
            tmp_path
            / "with_marker.py": f"# {PRESERVE_START_TOKEN}\nx\n{PRESERVE_END_TOKEN}\n",
            tmp_path
            / "nested"
            / "also.txt": f"{PRESERVE_START_TOKEN} a\ny\n{PRESERVE_END_TOKEN} a",
            tmp_path / "plain.py": "nothing special here",
        }
    )
    assert find_marker_files(tmp_path) == {
        Path("with_marker.py"),
        Path("nested/also.txt"),
    }


def test_capture_honors_explicit_relpaths(tmp_path: Path) -> None:
    build_file_tree(
        {
            tmp_path
            / "a.py": f"# {PRESERVE_START_TOKEN} k\nMINE\n# {PRESERVE_END_TOKEN} k\n",
            tmp_path
            / "b.py": f"# {PRESERVE_START_TOKEN} k\nOTHER\n# {PRESERVE_END_TOKEN} k\n",
        }
    )
    # Only the explicitly listed file is inspected, even though both match.
    captured = capture_preserved_regions(tmp_path, [Path("a.py")])
    assert set(captured) == {Path("a.py")}
    assert captured[Path("a.py")]["k"] == "MINE\n"


# Integration tests exercising the full ``copier update`` flow.


def _build_template_v1(src: Path) -> None:
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "app.py.jinja": (
                f"""\
                HEADER = "header v1"

                # {PRESERVE_START_TOKEN} greeting
                def greeting() -> str:
                    return "dummy v1"
                # {PRESERVE_END_TOKEN} greeting

                FOOTER = "footer v1"
                """
            ),
        }
    )
    with local.cwd(src):
        git("init")
        git("add", "-A")
        git("commit", "-m", "v1")
        git("tag", "v1")


def test_update_preserves_customized_region(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The developer's region survives while surrounding content updates."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    _build_template_v1(src)

    run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="v1")
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "generated")

    # Developer replaces the dummy body with a real implementation.
    app = dst / "app.py"
    app.write_text(
        app.read_text(encoding="utf-8").replace(
            'return "dummy v1"', 'return "Hello, developer!"'
        ),
        encoding="utf-8",
    )
    with local.cwd(dst):
        git("commit", "-am", "customize greeting")

    # Template v2 changes BOTH the surrounding content and the dummy body.
    build_file_tree(
        {
            src / "app.py.jinja": (
                f"""\
                HEADER = "header v2"

                # {PRESERVE_START_TOKEN} greeting
                def greeting() -> str:
                    return "dummy v2"
                # {PRESERVE_END_TOKEN} greeting

                FOOTER = "footer v2"
                """
            ),
        }
    )
    with local.cwd(src):
        git("commit", "-am", "v2")
        git("tag", "v2")

    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    result = app.read_text(encoding="utf-8")
    assert 'return "Hello, developer!"' in result  # region preserved
    assert "dummy v2" not in result  # template change ignored inside region
    assert 'HEADER = "header v2"' in result  # surroundings updated
    assert 'FOOTER = "footer v2"' in result
    assert "<<<<<<<" not in result  # no merge conflict


def test_update_without_region_change_has_no_conflict(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A region the template never changes still keeps the developer's content."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    _build_template_v1(src)

    run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="v1")
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "generated")

    app = dst / "app.py"
    app.write_text(
        app.read_text(encoding="utf-8").replace('return "dummy v1"', 'return "custom"'),
        encoding="utf-8",
    )
    with local.cwd(dst):
        git("commit", "-am", "customize")

    # v2 only touches the surrounding lines - the region is byte-for-byte the same.
    build_file_tree(
        {
            src / "app.py.jinja": (
                f"""\
                HEADER = "header v2"

                # {PRESERVE_START_TOKEN} greeting
                def greeting() -> str:
                    return "dummy v1"
                # {PRESERVE_END_TOKEN} greeting

                FOOTER = "footer v2"
                """
            ),
        }
    )
    with local.cwd(src):
        git("commit", "-am", "v2")
        git("tag", "v2")

    run_update(dst, defaults=True, overwrite=True, vcs_ref="v2")

    result = app.read_text(encoding="utf-8")
    assert 'return "custom"' in result
    assert 'HEADER = "header v2"' in result
    assert "<<<<<<<" not in result
