from __future__ import annotations

import pexpect
import pytest

from .helpers import COPIER_PATH, Keyboard, Spawn, build_file_tree, expect_prompt


def test_shortcuts_disabled_by_default(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """Shortcuts are disabled by default, so numbers don't select choices."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("3")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "first"


def test_shortcuts_disabled(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """When shortcuts are disabled, numbers don't select choices."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                    use_shortcuts: false
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("3")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "first"


def test_shortcuts_enabled(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """When shortcuts are enabled, numbers select choices."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                    use_shortcuts: true
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("3")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "third"


def test_multiselect_with_shortcuts_not_supported(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """When shortcuts and multiselect are both enabled, a ValidationError is raised."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    multiselect: true
                    choices:
                        one: first
                        two: second
                        three: third
                    use_shortcuts: true
                """
            )
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    tui.expect_exact(pexpect.EOF)
    assert tui.exitstatus != 0
    assert tui.proc.returncode != 0
    assert (
        "pydantic_core._pydantic_core.ValidationError: 1 validation error"
        in str(tui.before).split("\n")[-3]
    )


def test_search_filter_disabled_by_default(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """Search filter is disabled by default, so typing doesn't narrow choices."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("tw")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "first"


def test_search_filter_disabled(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """When search filter is disabled, typing doesn't narrow choices."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                    use_search_filter: false
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("tw")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "first"


def test_search_filter_enabled(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """When search filter is enabled, typing narrows choices to matching options."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                    use_search_filter: true
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "select", "str", help="Select one option only")
    tui.send("tw")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "second"


def test_search_filter_and_shortcut_not_supported(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """
    When search filter and shortcuts are enabled, a ValidationError is raised.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                select:
                    type: str
                    help: Select one option only
                    default: first
                    choices:
                        one: first
                        two: second
                        three: third
                        four: forth
                    use_search_filter: true
                    use_shortcuts: true
                """
            ),
            src / "result.jinja": "{{ select }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    tui.expect_exact(pexpect.EOF)
    assert tui.exitstatus != 0
    assert tui.proc.returncode != 0
    assert (
        "pydantic_core._pydantic_core.ValidationError: 1 validation error"
        in str(tui.before).split("\n")[-3]
    )


def test_multiselect_with_search_filter(
    tmp_path_factory: pytest.TempPathFactory, spawn: Spawn
) -> None:
    """Search filter works with multiselect prompts."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": (
                """\
                checkbox:
                    type: str
                    help: Select any option
                    multiselect: true
                    choices:
                        one: first
                        two: second
                        three: third
                    use_search_filter: true
                """
            ),
            src / "result.jinja": "{{ checkbox }}",
        }
    )
    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))
    expect_prompt(tui, "checkbox", "str", help="Select any option")
    tui.send("tw ")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "result").read_text() == "['second']"
