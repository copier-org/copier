from __future__ import annotations

from collections import deque
from textwrap import dedent

import pexpect
import pytest
from plumbum import local

from .helpers import (
    COPIER_PATH,
    Keyboard,
    Spawn,
    build_file_tree,
    expect_prompt,
)


@pytest.mark.parametrize(
    "copier_file, input_select, result",
    [
        (
            """\
            select:
                type: str
                help: Select one option only
                use_shortcuts: true
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            checkbox:
                type: str
                help: Select any
                multiselect: true
                use_search_filter: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: fourth
            """,
            "3",
            dedent(
                """\
                    select: "third"
                    checkbox: ["third"]
                """,
            ),
        ),
        (
            """\
            select:
                type: str
                help: Select one option only
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            checkbox:
                type: str
                help: Select any
                multiselect: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: fourth
            """,
            "3",
            dedent(
                """\
                    select: "first"
                    checkbox: ["first"]
                """
            ),
        ),
        (
            """\
            select:
                type: str
                help: Select one option only
                use_shortcuts: true
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            checkbox:
                type: str
                help: Select any
                multiselect: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: fourth
            """,
            "3",
            dedent(
                """\
                    select: "third"
                    checkbox: ["first"]
                """
            ),
        ),
        (
            """\
            select:
                type: str
                help: Select one option only
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            checkbox:
                type: str
                help: Select any
                multiselect: true
                use_search_filter: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: fourth
            """,
            "3",
            dedent(
                """\
                    select: "first"
                    checkbox: ["third"]
                """
            ),
        ),
        (
            """\
            select:
                type: str
                help: Select one option only
                use_search_filter: true
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            checkbox:
                type: str
                help: Select any
                multiselect: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: fourth
            """,
            "tw",
            dedent(
                """\
                    select: "second"
                    checkbox: ["first"]
                """
            ),
        ),
    ],
)
def test_shortcuts(
    tmp_path_factory: pytest.TempPathFactory,
    copier_file: str,
    input_select: str,
    result: str,
    spawn: Spawn,
) -> None:
    """Test shortcuts."""

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": copier_file,
                "results.txt.jinja": """\
                    select: {{select|tojson}}
                    checkbox: {{checkbox|tojson}}
                """,
            }
        )

    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))

    expect_prompt(tui, "select", "str", help="Select one option only")
    deque(
        map(
            tui.expect_exact,
            [
                "one",
                "two",
                "three",
            ],
        )
    )
    tui.send(input_select)
    tui.send(Keyboard.Enter)

    expect_prompt(tui, "checkbox", "str", help="Select any")
    deque(
        map(
            tui.expect_exact,
            ["one", "two", "three", "four"],
        )
    )
    tui.send("th ")
    tui.send(Keyboard.Enter)
    tui.expect_exact(pexpect.EOF)
    assert (dst / "results.txt").read_text() == result
