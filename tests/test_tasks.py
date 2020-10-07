import subprocess

import pytest
from plumbum import local
from plumbum.cmd import git

import copier
from copier.config import make_config
from copier.main import update_diff

from .helpers import DATA, render


def test_render_tasks(tmp_path):
    tasks = ["touch [[ myvar ]]/1.txt", "touch [[ myvar ]]/2.txt"]
    render(tmp_path, tasks=tasks)
    assert (tmp_path / DATA["myvar"] / "1.txt").exists()
    assert (tmp_path / DATA["myvar"] / "2.txt").exists()


def test_copy_tasks(tmp_path):
    copier.copy("tests/demo_tasks", tmp_path, quiet=True)
    assert (tmp_path / "hello").exists()
    assert (tmp_path / "hello").is_dir()
    assert (tmp_path / "hello" / "world").exists()


def test_set_stage_env_var(tmp_path):
    copier.copy("tests/demo_tasks_stage", tmp_path, quiet=True)
    assert (tmp_path / "hello").exists()
    assert (tmp_path / "hello").is_dir()
    assert (tmp_path / "hello" / "task").exists()


def test_set_operation_env_var(tmp_path):
    copier.copy("tests/demo_tasks_operation", tmp_path, quiet=True)
    assert (tmp_path / "operation").exists()
    assert (tmp_path / "operation").is_dir()
    assert (tmp_path / "operation" / "copy").exists()

    with local.cwd(tmp_path):
        git("init")
        git("add", ".")
        git("commit", "-m", "v1")

    # first update should succeed
    conf = make_config("./tests/demo_tasks_operation", str(tmp_path), force=True)
    update_diff(conf)
    assert (tmp_path / "operation" / "update").exists()
    assert not (tmp_path / "operation" / "copy").exists()

    with local.cwd(tmp_path):
        git("add", ".")
        git("commit", "-m", "v2")

    # second update should fail while trying to remove
    # operation/copy, since it was deleted in the first update
    conf = make_config("./tests/demo_tasks_operation", str(tmp_path), force=True)
    with pytest.raises(subprocess.CalledProcessError, match="bash update.sh"):
        update_diff(conf)
