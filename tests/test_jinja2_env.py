from __future__ import annotations

import sys
from pathlib import PurePath, PurePosixPath, PureWindowsPath

import pytest
from jinja2.exceptions import SecurityError

from copier._jinja_ext import SandboxedEnvironment
from copier._settings import SettingsModel


@pytest.mark.parametrize("path_type", [PurePath, PurePosixPath, PureWindowsPath])
@pytest.mark.parametrize(
    "expression",
    [
        "{{ path.parser.os.getcwd() }}",
        "{{ path['parser'].os.getcwd() }}",
        "{{ (path|attr('parser')).os.getcwd() }}",
        "{% set m = path.parser %}{{ m.os.getcwd() }}",
        "{% for m in [path.parser] %}{{ m.os.getcwd() }}{% endfor %}",
        "{{ [path]|map(attribute='parser.os.getcwd')|list }}",
        "{{ path.parser.os.popen('echo test').read() }}",
    ],
)
@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="`PurePath.parser` was added in Python 3.13"
)
def test_purepath_parser_attribute_is_unsafe(
    expression: str, path_type: type[PurePath]
) -> None:
    """`PurePath.parser` holds `posixpath`/`ntpath`, so `os` must stay out of reach."""
    env = SandboxedEnvironment()
    with pytest.raises(SecurityError):
        env.from_string(expression).render(path=path_type("/src/tpl"))


@pytest.mark.parametrize(
    "expression", ["{{ path.parser is defined }}", "{{ path|attr('parser') }}"]
)
@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="`PurePath.parser` was added in Python 3.13"
)
def test_purepath_parser_attribute_yields_undefined(expression: str) -> None:
    """The blocked attribute resolves to an unusable value, as Jinja does."""
    env = SandboxedEnvironment()
    rendered = env.from_string(expression).render(path=PurePosixPath("/src/tpl"))
    assert "module" not in rendered
    assert rendered in {"False", ""}


@pytest.mark.parametrize(
    "attribute",
    ["from_file", "parse_file", "parse_raw"],
)
@pytest.mark.parametrize(
    "access",
    [
        "settings.{attribute}",
        "settings[{attribute!r}]",
        "settings|attr({attribute!r})",
    ],
)
def test_settings_capability_is_unsafe(attribute: str, access: str) -> None:
    """File-loading settings methods are not part of the template interface."""
    env = SandboxedEnvironment()
    expression = access.format(attribute=attribute)
    rendered = env.from_string(f"{{{{ ({expression}) is defined }}}}").render(
        settings=SettingsModel()
    )
    assert rendered == "False"
