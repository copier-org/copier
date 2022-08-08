import platform
from pathlib import Path
from io import StringIO
import pytest
import tempfile
import filecmp

from copier.main import run_auto

from .helpers import PROJECT_TEMPLATE, build_file_tree
from plumbum.cmd import git

def _ephemeral_git_repo():
    d = tempfile.mkdtemp()
    git("-C", d, "init")
    return Path(d)

def test_force_overwrite():
    src = _ephemeral_git_repo()
    dst = _ephemeral_git_repo()
    build_file_tree(
        {
            src / "copier.yml": "_force_overwrite: ['aaaa.txt']",
            src / "aaaa.txt": "Template",
            src / "{{_copier_conf.answers_file}}.jinja": "{{_copier_answers|to_nice_yaml}}"
        }
    )
    git("-C", src, "add", "-A")
    git("-C", src, "commit", "-m1")
    run_auto(str(src), dst, quiet=True)
    git("-C", dst, "add", "-A")
    git("-C", dst, "commit", "-m1")
    build_file_tree(
        {
            dst / "aaaa.txt": "Repo"
        }
    )
    git("-C", dst, "add", "-A")
    git("-C", dst, "commit", "-m1")
    run_auto(None, dst, quiet=True)

    assert (dst / "aaaa.txt").exists()
    assert (filecmp.cmp(src/"aaaa.txt", dst/"aaaa.txt", shallow=False))


def test_force_overwrite_extended(monkeypatch):
    src = _ephemeral_git_repo()
    dst = _ephemeral_git_repo()
    build_file_tree(
        {
            src / "copier.yml": """
                _force_overwrite:
                    - "*.txt"
                    - "!foo.txt"
            """,
            src / "aaaa.txt": "Template",
            src / "{{_copier_conf.answers_file}}.jinja": "{{_copier_answers|to_nice_yaml}}",
            src / "foo.txt": "Template"
        }
    )
    git("-C", src, "add", "-A")
    git("-C", src, "commit", "-m1")
    run_auto(str(src), dst, quiet=True)
    git("-C", dst, "add", "-A")
    git("-C", dst, "commit", "-m1")
    build_file_tree(
        {
            dst / "aaaa.txt": "Repo",
            dst / "foo.txt": "Repo"
        }
    )
    git("-C", dst, "add", "-A")
    git("-C", dst, "commit", "-m1")
    monkeypatch.setattr('sys.stdin', StringIO("n"))
    run_auto(None, dst, quiet=True, defaults=True, overwrite=False)

    assert (dst / "aaaa.txt").exists()
    assert (filecmp.cmp(src/"aaaa.txt", dst/"aaaa.txt", shallow=False))
    assert not (filecmp.cmp(src/"foo.txt", dst/"foo.txt", shallow=False))
