from pathlib import Path
from shlex import split

import pytest

import copier
from copier.cli import make_parser, get_cli_args, run

SIMPLE_DEMO_PATH = Path(__file__).parent / "demo_simple"


@pytest.mark.parametrize(
    "base_config, arg_config, exception",
    (
        (None, ({},), TypeError),
        ({}, None, TypeError),
        ({}, ({},), KeyError),
        ({}, ({"args": None},), TypeError),
    ),
)
def test_make_parser_bad_config(base_config, arg_config, exception):
    with pytest.raises(exception):
        make_parser(base_config, arg_config)


@pytest.mark.parametrize("args_", (None, {}, {"source": "."}, {"dest": "."}))
def test_invalid_cli_args(args_):
    with pytest.raises(SystemExit):
        get_cli_args(args_)


@pytest.mark.parametrize(
    "arg, kw, expected",
    (
        # PATHS
        ("--extra-paths a/ b/ c/", "extra_paths", ["a/", "b/", "c/"]),
        ("--exclude a/ b/ c/", "exclude", ["a/", "b/", "c/"]),
        ("--include a/ b/ c/", "include", ["a/", "b/", "c/"]),
        # FLAGS
        ("--pretend", "pretend", True),
        ("--force", "force", True),
        ("--skip", "skip", True),
        ("--quiet", "quiet", True),
    ),
)
def test_cli_args(arg, kw, expected):
    args_ = f"src_path/ dst_path/ {arg}"
    kwargs = get_cli_args(split(args_))
    assert kw in kwargs
    assert kwargs[kw] == expected


def test_good_cli_run(dst, monkeypatch):
    def fake_cli_args(*_args, **_kwargs):
        return {"source": SIMPLE_DEMO_PATH, "dest": dst, "quiet": True}

    monkeypatch.setattr(copier.cli, "get_cli_args", fake_cli_args)

    run()
    a_txt = dst / "a.txt"
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text().strip() == "EXAMPLE_CONTENT"
