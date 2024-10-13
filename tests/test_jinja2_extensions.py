from __future__ import annotations

import json
import platform
import re
import sys
from contextlib import AbstractContextManager, nullcontext as does_not_raise
from datetime import datetime
from os.path import expanduser, expandvars
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, UndefinedError
from jinja2.ext import Extension
from time_machine import travel

import copier

from .helpers import PROJECT_TEMPLATE, build_file_tree

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    # HACK: This is a workaround for bad type information of `ZoneInfo`.
    # See https://github.com/pganssle/zoneinfo/issues/125.
    from backports.zoneinfo._zoneinfo import ZoneInfo


class FilterExtension(Extension):
    """Jinja2 extension to add a filter to the Jinja2 environment."""

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)

        def super_filter(obj: Any) -> str:
            return str(obj) + " super filter!"

        environment.filters["super_filter"] = super_filter


class GlobalsExtension(Extension):
    """Jinja2 extension to add global variables to the Jinja2 environment."""

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)

        def super_func(argument: Any) -> str:
            return str(argument) + " super func!"

        environment.globals.update(super_func=super_func)
        environment.globals.update(super_var="super var!")


def test_default_jinja2_extensions(tmp_path: Path) -> None:
    copier.run_copy(str(PROJECT_TEMPLATE) + "_extensions_default", tmp_path)
    super_file = tmp_path / "super_file.md"
    assert super_file.exists()
    assert super_file.read_text() == "path\n"


def test_additional_jinja2_extensions(tmp_path: Path) -> None:
    copier.run_copy(
        str(PROJECT_TEMPLATE) + "_extensions_additional", tmp_path, unsafe=True
    )
    super_file = tmp_path / "super_file.md"
    assert super_file.exists()
    assert super_file.read_text() == "super var! super func! super filter!\n"


def test_to_json_filter_with_conf(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "conf.json.jinja": "{{ _copier_conf|to_json }}",
        }
    )
    copier.run_copy(str(src), dst)
    conf_file = dst / "conf.json"
    assert conf_file.exists()
    # must not raise an error
    assert json.loads(conf_file.read_text())


@pytest.mark.parametrize(
    ("template", "value", "expected"),
    [
        # b64decode
        pytest.param(
            "{{ value | b64decode }}",
            "MTIz",
            "123",
            id="b64decode",
        ),
        # b64encode
        pytest.param(
            "{{ value | b64encode }}",
            "123",
            "MTIz",
            id="b64encode",
        ),
        # basename
        pytest.param(
            "{{ value | basename }}",
            "/etc/asdf/foo.txt",
            "foo.txt",
            id="basename",
        ),
        # win_basename
        pytest.param(
            "{{ value | win_basename }}",
            "etc\\asdf\\foo.txt",
            "foo.txt",
            id="win_basename",
        ),
        # win_splitdrive
        pytest.param(
            "{{ value | win_splitdrive | join(' & ') }}",
            "C:\\etc\\asdf\\foo.txt",
            "C: & \\etc\\asdf\\foo.txt",
            id="win_splitdrive",
        ),
        pytest.param(
            "{{ value | win_splitdrive | join(' & ') }}",
            "C:/etc/asdf/foo.txt",
            "C: & /etc/asdf/foo.txt",
            id="win_splitdrive with forward slash",
        ),
        # dirname
        pytest.param(
            "{{ value | dirname }}",
            "/etc/asdf/foo.txt",
            "/etc/asdf",
            id="dirname",
        ),
        # win_dirname
        pytest.param(
            "{{ value | win_dirname }}",
            "etc\\asdf\\foo.txt",
            "etc\\asdf",
            id="win_dirname",
        ),
        pytest.param(
            "{{ value | win_dirname }}",
            "etc/asdf/foo.txt",
            "etc/asdf",
            id="win_dirname with forward slash",
        ),
        pytest.param(
            "{{ value | win_dirname }}",
            "C:\\etc\\asdf\\foo.txt",
            "C:\\etc\\asdf",
            id="win_dirname with drive",
        ),
        pytest.param(
            "{{ value | win_dirname }}",
            "C:/etc/asdf/foo.txt",
            "C:/etc/asdf",
            id="win_dirname with drive and forward slash",
        ),
        # expanduser
        pytest.param(
            "{{ value | expanduser }}",
            "~/etc/asdf/foo.txt",
            f'{expanduser("~")}/etc/asdf/foo.txt',
            id="expanduser",
        ),
        # expandvars
        pytest.param(
            "{{ value | expandvars }}",
            "$HOME/etc/asdf/foo.txt",
            f'{expandvars("$HOME")}/etc/asdf/foo.txt',
            id="expandvars",
        ),
        # realpath
        pytest.param(
            "{{ value | realpath }}",
            "/etc/../asdf/foo.txt",
            "/asdf/foo.txt",
            marks=pytest.mark.skipif(
                condition=platform.system() != "Linux",
                reason="canonical path is platform-specific",
            ),
            id="realpath",
        ),
        # relpath
        pytest.param(
            "{{ value | relpath('/etc') }}",
            "/etc/asdf/foo.txt",
            "asdf/foo.txt",
            marks=pytest.mark.skipif(
                condition=platform.system() not in {"Linux", "Darwin"},
                reason="relative path on Unix",
            ),
            id="relpath (Unix)",
        ),
        pytest.param(
            "{{ value | relpath('C:\\Temp') }}",
            "C:\\Temp\\asdf\\foo.txt",
            "asdf\\foo.txt",
            marks=pytest.mark.skipif(
                condition=platform.system() != "Windows",
                reason="relative path on Windows",
            ),
            id="relpath (Windows)",
        ),
        # splitext
        pytest.param(
            "{{ value | splitext | join(' + ') }}",
            "foo.txt",
            "foo + .txt",
            id="splitext",
        ),
        # bool
        pytest.param(
            "{{ value | bool is true }}",
            "1",
            "True",
            id='bool: "1" -> True',
        ),
        pytest.param(
            "{{ value | bool is false }}",
            "0",
            "True",
            id='bool: "0" -> False',
        ),
        pytest.param(
            "{{ value | bool is true }}",
            "True",
            "True",
            id='bool: "True" -> True',
        ),
        pytest.param(
            "{{ value | bool is false }}",
            "false",
            "True",
            id='bool: "false" -> False',
        ),
        pytest.param(
            "{{ value | bool is true }}",
            "yes",
            "True",
            id='bool: "yes" -> True',
        ),
        pytest.param(
            "{{ value | bool is false }}",
            "no",
            "True",
            id='bool: "no" -> False',
        ),
        pytest.param(
            "{{ value | bool is true }}",
            "on",
            "True",
            id='bool: "on" -> True',
        ),
        pytest.param(
            "{{ value | bool is false }}",
            "off",
            "True",
            id='bool: "off" -> False',
        ),
        pytest.param(
            "{{ value | bool is true }}",
            True,
            "True",
            id="bool: True -> True",
        ),
        pytest.param(
            "{{ value | bool is false }}",
            False,
            "True",
            id="bool: False -> False",
        ),
        pytest.param(
            "{{ value | bool is none }}",
            None,
            "True",
            id="bool: None -> None",
        ),
        # checksum
        pytest.param(
            "{{ value | checksum }}",
            "test2",
            "109f4b3c50d7b0df729d299bc6f8e9ef9066971f",
            id="checksum",
        ),
        # sha1
        pytest.param(
            "{{ value | sha1 }}",
            "test2",
            "109f4b3c50d7b0df729d299bc6f8e9ef9066971f",
            id="sha1",
        ),
        # hash('sha1')
        pytest.param(
            "{{ value | hash('sha1') }}",
            "test2",
            "109f4b3c50d7b0df729d299bc6f8e9ef9066971f",
            id="hash('sha1')",
        ),
        # md5
        pytest.param(
            "{{ value | md5 }}",
            "test2",
            "ad0234829205b9033196ba818f7a872b",
            id="md5",
        ),
        # hash('md5')
        pytest.param(
            "{{ value | hash('md5') }}",
            "test2",
            "ad0234829205b9033196ba818f7a872b",
            id="hash('md5')",
        ),
        # to_json
        pytest.param(
            "{{ value | to_json }}",
            "München",
            r'"M\u00fcnchen"',
            id="to_json",
        ),
        pytest.param(
            "{{ value | to_json(ensure_ascii=False) }}",
            "München",
            '"München"',
            id="to_json(ensure_ascii=False)",
        ),
        # from_json
        pytest.param(
            "{{ value | from_json }}",
            '"München"',
            "München",
            id="from_json",
        ),
        # to_yaml
        pytest.param(
            "{{ value | to_yaml }}",
            {"k": True},
            "k: true\n",
            id="to_yaml",
        ),
        # from_yaml
        pytest.param(
            "{{ value | from_yaml == {'k': true} }}",
            "k: true",
            "True",
            id="from_yaml",
        ),
        # from_yaml_all
        pytest.param(
            """\
            {%- set result = value | from_yaml_all -%}
            {{- result is iterable -}}|
            {{- result is not sequence -}}|
            {{- result | list -}}
            """,
            "k1: v1\n---\nk2: v2",
            "True|True|[{'k1': 'v1'}, {'k2': 'v2'}]",
            id="from_yaml_all",
        ),
        # mandatory
        pytest.param(
            "{{ value | mandatory }}",
            "test2",
            "test2",
            id="mandatory: passthrough",
        ),
        pytest.param(
            "{{ undef | mandatory }}",
            "",
            pytest.raises(
                UndefinedError,
                match=re.escape("Mandatory variable `undef` is undefined"),
            ),
            id="mandatory: undefined variable",
        ),
        # to_uuid
        pytest.param(
            "{{ value | to_uuid }}",
            "test2",
            "daf9c796-57b5-57c0-aa86-6637fc9c3c88",
            id="to_uuid",
        ),
        pytest.param(
            "{{ value | to_uuid('11111111-2222-3333-4444-555555555555') }}",
            "test2",
            "eb47636c-32aa-5e19-aba9-e19ffafacbc2",
            id="to_uuid: custom namespace",
        ),
        # quote
        pytest.param(
            "echo {{ value | quote }}",
            "hello world",
            "echo 'hello world'",
            id="quote",
        ),
        pytest.param(
            "echo {{ value | quote }}",
            "hello world",
            "echo 'hello world'",
            id="quote",
        ),
        # strftime
        pytest.param(
            "{{ value | strftime }}",
            "%H:%M:%S",
            "02:03:04",
            marks=pytest.mark.skipif(
                condition=platform.system() not in {"Linux", "Darwin"},
                reason="time zone mocking via `time.tzset()` only works on Unix",
            ),
            id="strftime",
        ),
        pytest.param(
            "{{ value | strftime(seconds=12345) }}",
            "%H:%M:%S",
            "19:25:45",
            marks=pytest.mark.skipif(
                condition=platform.system() not in {"Linux", "Darwin"},
                reason="time zone mocking via `time.tzset()` only works on Unix",
            ),
            id="strftime: custom seconds",
        ),
        pytest.param(
            "{{ value | strftime(utc=True) }}",
            "%H:%M:%S",
            "10:03:04",
            id="strftime: utc",
        ),
        # ternary
        pytest.param(
            "{{ value | ternary('yes', 'no') }}",
            True,
            "yes",
            id="ternary: true",
        ),
        pytest.param(
            "{{ value | ternary('yes', 'no') }}",
            False,
            "no",
            id="ternary: false",
        ),
        pytest.param(
            "{{ value | ternary('yes', 'no') is none }}",
            None,
            "True",
            id="ternary: none (default)",
        ),
        pytest.param(
            "{{ value | ternary('yes', 'no', 'null') }}",
            None,
            "null",
            id="ternary: none (custom)",
        ),
        # to_nice_json
        pytest.param(
            "{{ value | to_nice_json }}",
            {"x": [1, 2], "k": "v"},
            '{\n    "k": "v",\n    "x": [\n        1,\n        2\n    ]\n}',
            id="to_nice_json",
        ),
        pytest.param(
            "{{ value | to_nice_json(indent=2) }}",
            {"x": [1, 2], "k": "v"},
            '{\n  "k": "v",\n  "x": [\n    1,\n    2\n  ]\n}',
            id="to_nice_json: custom indent",
        ),
        # to_nice_yaml
        pytest.param(
            "{{ value | to_nice_yaml }}",
            {"x": {"y": [1, 2]}, "k": "v"},
            "k: v\nx:\n    y:\n    - 1\n    - 2\n",
            id="to_nice_yaml",
        ),
        pytest.param(
            "{{ value | to_nice_yaml(indent=2) }}",
            {"x": {"y": [1, 2]}, "k": "v"},
            "k: v\nx:\n  y:\n  - 1\n  - 2\n",
            id="to_nice_yaml: custom indent",
        ),
        # to_datetime
        pytest.param(
            "{{ (('2016-08-14 20:00:12' | to_datetime) - ('2016-08-12' | to_datetime('%Y-%m-%d'))).days }}",
            None,
            "2",
            id="to_datetime",
        ),
        # shuffle
        pytest.param(
            "{{ value | shuffle(seed='123') | join(', ') }}",
            [1, 2, 3],
            "2, 1, 3",
            id="shuffle",
        ),
        # ans_random
        pytest.param(
            "{{ value | ans_random(seed='123') }}",
            100,
            "93",
            id="ans_random: stop",
        ),
        pytest.param(
            "{{ value | ans_random(start=94, step=2, seed='123') }}",
            100,
            "98",
            id="ans_random: start/stop/step",
        ),
        # flatten
        pytest.param(
            "{{ value | flatten }}",
            ["a", [1, [2, [None, 3]]]],
            "['a', 1, 2, 3]",
            id="flatten",
        ),
        pytest.param(
            "{{ value | flatten(levels=0) }}",
            ["a", [1, [2, [None, 3]]]],
            "['a', [1, [2, [None, 3]]]]",
            id="flatten: levels=0",
        ),
        pytest.param(
            "{{ value | flatten(levels=1) }}",
            ["a", [1, [2, [None, 3]]]],
            "['a', 1, [2, [None, 3]]]",
            id="flatten: levels=1",
        ),
        pytest.param(
            "{{ value | flatten(skip_nulls=False) }}",
            ["a", [1, [2, [None, 3]]]],
            "['a', 1, 2, None, 3]",
            id="flatten: skip_nulls=False",
        ),
        # random_mac
        pytest.param(
            "{{ value | random_mac(seed='123') }}",
            "52:54:00",
            "52:54:00:25:a4:fc",
            id="random_mac",
        ),
        pytest.param(
            "{{ value | random_mac(seed='123') }}",
            "52:54:00:25:a4:fc",
            pytest.raises(
                ValueError,
                match=re.escape(
                    "Invalid MAC address prefix 52:54:00:25:a4:fc: too many parts"
                ),
            ),
            id="random_mac: too many parts",
        ),
        pytest.param(
            "{{ value | random_mac(seed='123') }}",
            "52:54:gg",
            pytest.raises(
                ValueError,
                match=re.escape(
                    "Invalid MAC address prefix 52:54:gg: gg is not a hexadecimal byte"
                ),
            ),
            id="random_mac: invalid hexadecimal byte",
        ),
        # regex_escape
        pytest.param(
            "{{ value | regex_escape }}",
            "^f.*o(.*)$",
            "\\^f\\.\\*o\\(\\.\\*\\)\\$",
            id="regex_escape",
        ),
        # regex_search
        pytest.param(
            "{{ value | regex_search('database[0-9]+') }}",
            "server1/database42",
            "database42",
            id="regex_search",
        ),
        pytest.param(
            "{{ value | regex_search('(?i)server([0-9]+)') }}",
            "sErver1/database42",
            "sErver1",
            id="regex_search: inline flags",
        ),
        pytest.param(
            "{{ value | regex_search('^bar', multiline=True, ignorecase=True) }}",
            "foo\nBAR",
            "BAR",
            id="regex_search: keyword argument flags",
        ),
        pytest.param(
            "{{ value | regex_search('server([0-9]+)/database([0-9]+)', '\\\\1', '\\\\2') }}",
            "server1/database42",
            "['1', '42']",
            id="regex_search: backrefs (index)",
        ),
        pytest.param(
            "{{ value | regex_search('(?P<dividend>[0-9]+)/(?P<divisor>[0-9]+)', '\\\\g<dividend>', '\\\\g<divisor>') }}",
            "21/42",
            "['21', '42']",
            id="regex_search: backrefs (name)",
        ),
        pytest.param(
            "{{ value | regex_search('(?P<dividend>[0-9]+)/(?P<divisor>[0-9]+)', 'INVALID') }}",
            "21/42",
            pytest.raises(
                ValueError,
                match=re.escape("Invalid backref format"),
            ),
            id="regex_search: invalid backref format",
        ),
        # regex_replace
        pytest.param(
            "{{ value | regex_replace('^a.*i(.*)$', 'a\\\\1') }}",
            "ansible",
            "able",
            id="regex_replace",
        ),
        pytest.param(
            "{{ value | regex_replace('(?i)^a.*i(.*)$', 'a\\\\1') }}",
            "AnsIbLe",
            "abLe",
            id="regex_replace: inline flags",
        ),
        pytest.param(
            "{{ value | regex_replace('^a.*i(.*)$', 'a\\\\1', ignorecase=True) }}",
            "AnsIbLe",
            "abLe",
            id="regex_replace: keyword argument flags",
        ),
        # regex_findall
        pytest.param(
            "{{ value | regex_findall('\\\\b(?:[0-9]{1,3}\\\\.){3}[0-9]{1,3}\\\\b') }}",
            "Some DNS servers are 8.8.8.8 and 8.8.4.4",
            "['8.8.8.8', '8.8.4.4']",
            id="regex_findall",
        ),
        pytest.param(
            "{{ value | regex_findall('(?im)^.ar$') }}",
            "CAR\ntar\nfoo\nbar\n",
            "['CAR', 'tar', 'bar']",
            id="regex_findall: inline flags",
        ),
        pytest.param(
            "{{ value | regex_findall('^.ar$', multiline=True, ignorecase=True) }}",
            "CAR\ntar\nfoo\nbar\n",
            "['CAR', 'tar', 'bar']",
            id="regex_findall: keyword argument flags",
        ),
        # type_debug
        pytest.param(
            "{{ value | type_debug }}",
            "foo",
            "str",
            id="type_debug: str",
        ),
        pytest.param(
            "{{ value | type_debug }}",
            123,
            "int",
            id="type_debug: int",
        ),
        # extract
        pytest.param(
            "{{ value | extract(['a', 'b', 'c']) }}",
            1,
            "b",
            id="extract",
        ),
        pytest.param(
            "{{ value | extract(['a', 'b', 'c']) is undefined }}",
            3,
            "True",
            id="extract: undefined",
        ),
        pytest.param(
            "{{ value | extract([{'a': 1, 'b': 2, 'c': 3}, {'x': 9, 'y': 10}], morekeys='b') }}",
            0,
            "2",
            id="extract: nested",
        ),
        pytest.param(
            "{{ value | extract([{'a': 1, 'b': 2, 'c': 3}, {'x': 9, 'y': 10}], morekeys='z') is undefined }}",
            0,
            "True",
            id="extract: nested undefined",
        ),
    ],
)
@travel(datetime(1970, 1, 1, 2, 3, 4, tzinfo=ZoneInfo("America/Los_Angeles")))
def test_filters(
    tmp_path_factory: pytest.TempPathFactory,
    template: str,
    value: Any,
    expected: str | Exception,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "result.txt.jinja": template})
    with expected if isinstance(expected, AbstractContextManager) else does_not_raise():
        copier.run_copy(str(src), dst, data={"value": value})
        assert (dst / "result.txt").exists()
        assert (dst / "result.txt").read_text("utf-8") == expected


@pytest.mark.xfail(reason="cwd while rendering isn't destination root")
def test_filter_fileglob(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "result.txt.jinja": "{{ '**/*.txt' | fileglob | sort | join('|') }}",
            dst / "a.txt": "",
            dst / "b" / "c.txt": "",
        }
    )
    copier.run_copy(str(src), dst)
    assert (dst / "result.txt").exists()
    assert (dst / "result.txt").read_text() == f'a.txt|{Path("b", "c.txt")}'
