from pathlib import Path
from pydantic import ValidationError
import pytest

from ..copier.config.factory import make_config
from ..copier.config.objects import (
    ConfigData,
    EnvOps,
    Flags,
    DEFAULT_DATA,
    DEFAULT_EXCLUDE,
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
}


# Flags
@pytest.mark.parametrize(
    "data",
    (
        {"pretend": "not_a_bool"},
        {"quiet": "not_a_bool"},
        {"force": "not_a_bool"},
        {"skip": "not_a_bool"},
        {"cleanup_on_error": "not_a_bool"},
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
            assert err["msg"] == "Project template not found"
    else:
        raise AssertionError()


def test_config_data_good_data(dst):
    dst = Path(dst).expanduser().resolve()
    good_config_data = {
        "src_path": dst,
        "dst_path": dst,
        "data": DEFAULT_DATA,
        "extra_paths": [dst],
        "exclude": DEFAULT_EXCLUDE,
        "include": [],
        "skip_if_exists": ["skip_me"],
        "tasks": ["echo python rulez"],
        "envops": EnvOps(),
    }
    conf = ConfigData(**good_config_data)
    assert conf.dict() == good_config_data


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
    """Test if config sources are merged in the right order of precedence."""
    conf, flags = make_config(dst_path=dst, **test_input)
    assert is_subdict(expected, conf.dict())
