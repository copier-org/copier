from pathlib import Path
import re

import pytest

from .. import copier
from ..copier.user_data import (
    load_yaml_data,
    load_json_data,
    load_old_json_data,
    load_default_data,
)


@pytest.mark.parametrize(
    "template", ["tests/demo_yaml", "tests/demo_json", "tests/demo_json_old"]
)
def test_read_user_data(dst, template):
    copier.copy(template, dst, force=True)

    gen_file = dst / "user_data.txt"
    result = gen_file.read_text()
    print(result)
    expected = Path("tests/user_data.ref.txt").read_text()
    assert result == expected


def test_bad_yaml(capsys):
    assert {} == load_yaml_data("tests/demo_badyaml")


def test_invalid_yaml(capsys):
    assert {} == load_yaml_data("tests/demo_invalid")
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.yml", out)

    assert {} == load_json_data("tests/demo_invalid")
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.json", out)

    # TODO: Remove on version 3.0
    assert {} == load_old_json_data("tests/demo_invalid", warning=False)
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/voodoo\.json", out)

    assert {} == load_default_data("tests/demo_invalid", warning=False)
    assert re.search(r"INVALID", out)


def test_invalid_quiet(capsys):
    assert {} == load_default_data("tests/demo_invalid", quiet=True)
    out, err = capsys.readouterr()
    assert out == ""

    assert {} == load_old_json_data("tests/demo_invalid", quiet=True)
    out, err = capsys.readouterr()
    assert out == ""


def test_deprecated_msg(capsys):
    # TODO: Remove on version 3.0
    load_old_json_data("tests/demo_json_old")
    out, err = capsys.readouterr()
    assert re.search(r"`voodoo\.json` is deprecated", out)
