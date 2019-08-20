from pathlib import Path
import re

import pytest

import copier
from copier.user_data import (
    load_yaml_data,
    load_toml_data,
    load_json_data,
    load_old_json_data,
    load_config_data,
)


def test_config_data_is_loaded_from_file():
    config = load_config_data("tests/demo_data")
    config["_exclude"] = ["exclude1", "exclude2"]
    config["_include"] = ["include1", "include2"]
    config["_skip_if_exists"] = ["skip_if_exists1", "skip_if_exists2"]
    config["_tasks"] = ["touch 1", "touch 2"]
    config["_extra_paths"] = ["test"]


@pytest.mark.parametrize(
    "template",
    [
        "tests/demo_toml",
        "tests/demo_yaml",
        "tests/demo_yml",
        "tests/demo_json",
        "tests/demo_json_old",
    ],
)
def test_read_data(dst, template):
    copier.copy(template, dst, force=True)

    gen_file = dst / "user_data.txt"
    result = gen_file.read_text()
    print(result)
    expected = Path("tests/user_data.ref.txt").read_text()
    assert result == expected


def test_bad_toml(capsys):
    assert {} == load_toml_data("tests/demo_badtoml")


def test_invalid_toml(capsys):
    assert {} == load_yaml_data("tests/demo_invalid")
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.yml", out)

    assert {} == load_toml_data("tests/demo_invalid")
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.toml", out)

    assert {} == load_json_data("tests/demo_invalid")
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.json", out)

    # TODO: Remove on version 3.0
    assert {} == load_old_json_data("tests/demo_invalid", _warning=False)
    out, err = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/voodoo\.json", out)

    assert {} == load_config_data("tests/demo_invalid", _warning=False)
    assert re.search(r"INVALID", out)


def test_invalid_quiet(capsys):
    assert {} == load_config_data("tests/demo_invalid", quiet=True)
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
