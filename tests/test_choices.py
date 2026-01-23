from __future__ import annotations

from collections import deque
from textwrap import dedent
from typing import Any

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


def tui_test_template(
    tmp_path_factory: pytest.TempPathFactory,
    copier_file: str,
    tui_io: tuple[dict[str, Any]],
    result_template: str,
    result: str,
    spawn: Spawn,
) -> None:
    """Template for general test of tui.

    Use:
    > {
    >     "expect_prompt": {
    >         "name":,
    >         "type":,
    >         "help":,
    >     },
    >     "expect_exact": (),
    >     "send":(),
    > },
    """

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": copier_file,
                "results.txt.jinja": result_template,
            }
        )

    tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)))

    for _tui in tui_io:
        _expect_prompt = _tui["expect_prompt"]
        expect_prompt(
            tui,
            _expect_prompt["name"],
            _expect_prompt["type"],
            help=_expect_prompt["help"],
        )
        deque(map(tui.expect_exact, _tui["expect_exact"]))
        deque(map(tui.send, _tui["send"]))

    tui.expect_exact(pexpect.EOF)
    assert (dst / "results.txt").read_text() == result


@pytest.mark.parametrize(
    "copier_file, tui_io, result_template, result",
    [
        (
            # copier_file
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
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "select",
                        "type": "str",
                        "help": "Select one option only",
                    },
                    "expect_exact": ("one", "two", "three"),
                    "send": ("3", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                select: {{select|tojson}}
            """,
            # result
            dedent(
                """\
                    select: "third"
                """,
            ),
        ),
        (
            # copier_file
            """\
            select:
                type: str
                help: Select one option only
                use_shortcuts: false
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "select",
                        "type": "str",
                        "help": "Select one option only",
                    },
                    "expect_exact": ("one", "two", "three"),
                    "send": ("3", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                select: {{select|tojson}}
            """,
            # result
            dedent(
                """\
                    select: "first"
                """,
            ),
        ),
        (
            # copier_file
            """\
            select:
                type: str
                help: Select one option only
                use_shortcuts: true
                use_search_filter: true
                default: first
                choices:
                    one: first
                    two: second
                    three: third
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "select",
                        "type": "str",
                        "help": "Select one option only",
                    },
                    "expect_exact": ("one", "two", "three"),
                    "send": ("3", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                select: {{select|tojson}}
            """,
            # result
            dedent(
                """\
                    select: "first"
                """,
            ),
        ),
    ],
)
def test_use_shortcuts(
    tmp_path_factory: pytest.TempPathFactory,
    copier_file: str,
    tui_io: tuple[dict[str, Any]],
    result_template: str,
    result: str,
    spawn: Spawn,
) -> None:
    """Test `use_shortcuts`."""
    tui_test_template(
        tmp_path_factory=tmp_path_factory,
        copier_file=copier_file,
        tui_io=tui_io,
        result_template=result_template,
        result=result,
        spawn=spawn,
    )


@pytest.mark.parametrize(
    "copier_file, tui_io, result_template, result",
    [
        (
            # copier_file
            """\
            select:
                type: str
                help: Select one option only
                use_shortcuts: true
                use_search_filter: true
                default: first
                choices:
                    one: first
                    two: second
                    three: third
                    four: forth
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "select",
                        "type": "str",
                        "help": "Select one option only",
                    },
                    "expect_exact": ("one", "two", "three", "four"),
                    "send": ("3", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                select: {{select|tojson}}
            """,
            # result
            dedent(
                """\
                    select: "first"
                """,
            ),
        ),
        (
            # copier_file
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
                    four: forth
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "select",
                        "type": "str",
                        "help": "Select one option only",
                    },
                    "expect_exact": ("one", "two", "three", "four"),
                    "send": ("tw", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                select: {{select|tojson}}
            """,
            # result
            dedent(
                """\
                    select: "second"
                """,
            ),
        ),
        (
            # copier_file
            """\
            checkbox:
                type: str
                help: Select any option
                multiselect: true
                use_search_filter: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: forth
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "checkbox",
                        "type": "str",
                        "help": "Select any option",
                    },
                    "expect_exact": ("one", "two", "three", "four"),
                    "send": ("tw ", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                checkbox: {{checkbox|tojson}}
            """,
            # result
            dedent(
                """\
                    checkbox: ["second"]
                """,
            ),
        ),
        (
            # copier_file
            """\
            checkbox:
                type: str
                help: Select any option
                multiselect: true
                use_search_filter: true
                choices:
                    one: first
                    two: second
                    three: third
                    four: forth
            """,
            # tui_io
            (
                {
                    "expect_prompt": {
                        "name": "checkbox",
                        "type": "str",
                        "help": "Select any option",
                    },
                    "expect_exact": ("one", "two", "three", "four"),
                    "send": ("tr ", Keyboard.Enter),
                },
            ),
            # result_template
            """\
                checkbox: {{checkbox|tojson}}
            """,
            # result
            dedent(
                """\
                    checkbox: ["first"]
                """,
            ),
        ),
    ],
)
def test_use_search_filter(
    tmp_path_factory: pytest.TempPathFactory,
    copier_file: str,
    tui_io: tuple[dict[str, Any]],
    result_template: str,
    result: str,
    spawn: Spawn,
) -> None:
    """Test `use_search_filter`."""
    tui_test_template(
        tmp_path_factory=tmp_path_factory,
        copier_file=copier_file,
        tui_io=tui_io,
        result_template=result_template,
        result=result,
        spawn=spawn,
    )
