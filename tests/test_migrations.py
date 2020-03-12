from glob import glob
from pathlib import Path
from shutil import copytree

import py
import yaml
from plumbum import local
from plumbum.cmd import git

from copier import copy

from .helpers import PROJECT_TEMPLATE

SRC = Path(f"{PROJECT_TEMPLATE}_migrations").absolute()


def test_migrations_and_tasks(tmpdir: py.path.local):
    """Check migrations and tasks are run properly."""
    # Convert demo_migrations in a git repository with 2 versions
    git_src, dst = tmpdir / "src", tmpdir / "dst"
    copytree(SRC, git_src)
    with local.cwd(git_src):
        git("init")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1.0.0")
        git("commit", "--allow-empty", "-m2")
        git("tag", "v2.0")
    # Copy it in v1
    copy(src_path=str(git_src), dst_path=str(dst), vcs_ref="v1.0.0")
    # Check copy was OK
    assert (dst / "created-with-tasks.txt").read() == "task 1\ntask 2\n"
    assert not (dst / "delete-in-tasks.txt").exists()
    assert (dst / "delete-in-migration-v2.txt").isfile()
    assert not (dst / "migrations.py").exists()
    assert not (dst / "tasks.sh").exists()
    assert not glob(str(dst / "*-before.txt"))
    assert not glob(str(dst / "*-after.txt"))
    answers = yaml.safe_load((dst / ".copier-answers.yml").read())
    assert answers == {"_commit": "v1.0.0", "_src_path": str(git_src)}
    # Save changes in downstream repo
    with local.cwd(dst):
        git("add", ".")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("commit", "-m1")
    # Update it to v2
    copy(dst_path=str(dst), force=True)
    # Check update was OK
    assert (dst / "created-with-tasks.txt").read() == "task 1\ntask 2\n" * 2
    assert not (dst / "delete-in-tasks.txt").exists()
    assert not (dst / "delete-in-migration-v2.txt").exists()
    assert not (dst / "migrations.py").exists()
    assert not (dst / "tasks.sh").exists()
    assert (dst / "v1.0.0-v2-v2.0-before.json").isfile()
    assert (dst / "v1.0.0-v2-v2.0-after.json").isfile()
    answers = yaml.safe_load((dst / ".copier-answers.yml").read())
    assert answers == {"_commit": "v2.0", "_src_path": str(git_src)}
