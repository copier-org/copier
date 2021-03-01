from pathlib import Path
from stat import S_IREAD
from tempfile import TemporaryDirectory

from poethepoet.app import PoeThePoet
from plumbum.cmd import git


def test_lint():
    """Ensure source code formatting"""
    PoeThePoet(Path("."))(["lint", "--show-diff-on-failure", "--color=always"])


def test_types():
    """Ensure source code static typing."""
    PoeThePoet(Path("."))(["types"])


def test_temporary_directory_with_readonly_files_deletion():
    """Ensure temporary directories containing read-only files are properly deleted, whatever the OS."""
    with TemporaryDirectory() as tmp_dir:
        ro_file = Path(tmp_dir) /  "readonly.txt"
        with ro_file.open("w") as fp:
            fp.write("don't touch me!")
        ro_file.chmod(S_IREAD)
    assert not Path(tmp_dir).exists()


def test_temporary_directory_with_git_repo_deletion():
    """Ensure temporary directories containing git repositories are properly deleted, whatever the OS."""
    with TemporaryDirectory() as tmp_dir:
        git("clone", "--depth=1", ".", Path(tmp_dir) / "repo")
    assert not Path(tmp_dir).exists()
