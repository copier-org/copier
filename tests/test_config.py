import re
from pathlib import Path

import pytest
from pydantic import ValidationError

import copier
from copier.config.factory import make_config
from copier.config.objects import (
    DEFAULT_DATA,
    DEFAULT_EXCLUDE,
    ConfigData,
    EnvOps,
    Flags,
)
from copier.config.user_data import (
    InvalidConfigFileError,
    MultipleConfigFilesError,
    load_config_data,
    load_yaml_data,
)

GOOD_FLAGS = {
    "pretend": True,
    "quiet": False,
    "force": True,
    "skip": False,
    "cleanup_on_error": True,
}

GOOD_ENV_OPS = {
    "autoescape": True,
    "block_start_string": "<%",
    "block_end_string": "%>",
    "variable_start_string": "<<",
    "variable_end_string": ">>",
    "keep_trailing_newline": False,
    "i_am_not_a_member": None,
    "comment_end_string": "#>",
    "comment_start_string": "<#",
}


def test_config_data_is_loaded_from_file():
    config = load_config_data("tests/demo_data")
    assert config["_exclude"] == ["exclude1", "exclude2"]
    assert config["_include"] == ["include1", "include2"]
    assert config["_skip_if_exists"] == ["skip_if_exists1", "skip_if_exists2"]
    assert config["_tasks"] == ["touch 1", "touch 2"]
    assert config["_extra_paths"] == ["tests"]


@pytest.mark.parametrize("template", ["tests/demo_yaml", "tests/demo_yml"])
def test_read_data(dst, template):
    copier.copy(template, dst, force=True)
    gen_file = dst / "user_data.txt"
    result = gen_file.read_text()
    expected = Path("tests/reference_files/user_data.txt").read_text()
    assert result == expected


def test_invalid_yaml(capsys):
    conf_path = Path("tests/demo_invalid/copier.yml")
    with pytest.raises(InvalidConfigFileError):
        load_yaml_data(conf_path)
    out, _ = capsys.readouterr()
    assert re.search(r"INVALID.*tests/demo_invalid/copier\.yml", out)


def test_invalid_data(capsys):
    with pytest.raises(InvalidConfigFileError):
        load_config_data("tests/demo_invalid", _warning=False)
    out, _ = capsys.readouterr()
    assert re.search(r"INVALID", out)


def test_invalid_quiet(capsys):
    with pytest.raises(InvalidConfigFileError):
        load_config_data("tests/demo_invalid", quiet=True)
    out, _ = capsys.readouterr()
    assert out == ""


def test_multiple_config_file_error(capsys):
    with pytest.raises(MultipleConfigFilesError):
        load_config_data("tests/demo_multi_config", quiet=True)
    out, _ = capsys.readouterr()
    assert out == ""


# Flags
@pytest.mark.parametrize(
    "data",
    (
        {"pretend": "not_a_bool"},
        {"quiet": "not_a_bool"},
        {"force": "not_a_bool"},
        {"skip": "not_a_bool"},
        {"cleanup_on_error": "not_a_bool"},
        {"force": True, "skip": True},
    ),
)
def test_flags_bad_data(data):
    with pytest.raises(ValidationError):
        Flags(**data)


def test_flags_good_data():
    flags = Flags(**GOOD_FLAGS)
    assert flags.dict() == GOOD_FLAGS


def test_flags_extra_ignored():
    key = "i_am_not_a_member"
    flag_data = {key: "and_i_do_not_belong_here"}
    flags = Flags(**flag_data)
    assert key not in flags.dict()


# EnvOps
@pytest.mark.parametrize(
    "data",
    (
        {"autoescape": "not_a_bool"},
        {"block_start_string": None},
        {"block_end_string": None},
        {"variable_start_string": None},
        {"variable_end_string": None},
        {"keep_trailing_newline": "not_a_bool"},
    ),
)
def test_envops_bad_data(data):
    with pytest.raises(ValidationError):
        EnvOps(**data)


def test_envops_good_data():
    ops = EnvOps(**GOOD_ENV_OPS)
    assert ops.dict() == GOOD_ENV_OPS


# ConfigData
def test_config_data_paths_required():
    try:
        ConfigData(envops=EnvOps())
    except ValidationError as e:
        assert len(e.errors()) == 2
        for i, p in enumerate(("src_path", "dst_path")):
            err = e.errors()[i]
            assert err["loc"][0] == p
            assert err["type"] == "value_error.missing"
    else:
        raise AssertionError()


def test_config_data_paths_existing(dst):
    try:
        ConfigData(
            src_path="./i_do_not_exist",
            extra_paths=["./i_do_not_exist"],
            dst_path=dst,
            envops=EnvOps(),
        )
    except ValidationError as e:
        assert len(e.errors()) == 2
        for i, p in enumerate(("src_path", "extra_paths")):
            err = e.errors()[i]
            assert err["loc"][0] == p
            assert err["msg"] == "Project template not found."
    else:
        raise AssertionError()


def test_config_data_good_data(dst):
    dst = Path(dst).expanduser().resolve()
    expected = {
        "src_path": dst,
        "dst_path": dst,
        "data": DEFAULT_DATA,
        "extra_paths": [dst],
        "exclude": DEFAULT_EXCLUDE,
        "include": [],
        "original_src_path": None,
        "skip_if_exists": ["skip_me"],
        "tasks": ["echo python rulez"],
        "templates_suffix": ".tmpl",
        "envops": EnvOps(),
    }
    conf = ConfigData(**expected)
    expected["data"]["folder_name"] = dst.name
    assert conf.dict() == expected


def test_make_config_bad_data(dst):
    with pytest.raises(ValidationError):
        make_config("./i_do_not_exist", dst)


def is_subdict(small, big):
    return {**big, **small} == big


def test_make_config_good_data(dst):
    conf, flags = make_config("./tests/demo_data", dst)
    assert conf is not None
    assert flags is not None
    assert "folder_name" in conf.data
    assert conf.data["folder_name"] == dst.name
    assert conf.exclude == ["exclude1", "exclude2"]
    assert conf.include == ["include1", "include2"]
    assert conf.skip_if_exists == ["skip_if_exists1", "skip_if_exists2"]
    assert conf.tasks == ["touch 1", "touch 2"]
    assert conf.extra_paths == [Path("tests").resolve()]


@pytest.mark.parametrize(
    "test_input, expected",
    [
        # func_args > defaults
        ({"src_path": ".", "include": ["aaa"]}, {"include": ["aaa"]}),
        # user_data > defaults
        ({"src_path": "tests/demo_data"}, {"include": ["include1", "include2"]}),
        # func_args > user_data
        ({"src_path": "tests/demo_data", "include": ["aaa"]}, {"include": ["aaa"]}),
    ],
)
def test_make_config_precedence(dst, test_input, expected):
    conf, flags = make_config(dst_path=dst, **test_input)
    assert is_subdict(expected, conf.dict())
