import platform
from pathlib import Path
from stat import S_IREAD

import pytest
from plumbum.cmd import git
from poethepoet.app import PoeThePoet

from copier.tools import TemporaryDirectory


@pytest.mark.impure
@pytest.mark.skipif(
    condition=platform.system() == "Windows",
    reason="Windows does weird things with line endings.",
)
def test_lint():
    """Ensure source code formatting"""
    result = PoeThePoet(Path("."))(["lint", "--show-diff-on-failure", "--color=always"])
    assert result == 0


def test_types():
    """Ensure source code static typing."""
    result = PoeThePoet(Path("."))(["types"])
    assert result == 0


def test_temporary_directory_with_readonly_files_deletion():
    """Ensure temporary directories containing read-only files are properly deleted, whatever the OS."""
    with TemporaryDirectory() as tmp_dir:
        ro_file = Path(tmp_dir) / "readonly.txt"
        with ro_file.open("w") as fp:
            fp.write("don't touch me!")
        ro_file.chmod(S_IREAD)
    assert not Path(tmp_dir).exists()


def test_temporary_directory_with_git_repo_deletion():
    """Ensure temporary directories containing git repositories are properly deleted, whatever the OS."""
    with TemporaryDirectory() as tmp_dir:
        git("init")
    assert not Path(tmp_dir).exists()
