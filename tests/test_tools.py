import platform
from pathlib import Path
from stat import S_IREAD

import pytest
from plumbum.cmd import git
from poethepoet.app import PoeThePoet

from copier.tools import TemporaryDirectory, deepflatten


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
        git("clone", "--depth=1", ".", Path(tmp_dir) / "repo")
    assert not Path(tmp_dir).exists()


def test_deepflatten():
    """Ensure deepflatten works in simple usage"""
    result = deepflatten([1, [2, 3], 4], depth=1, types=(list,))
    assert list(result) == [1, 2, 3, 4]


def test_deepflatten_depth():
    """Ensure deepflatten depth works"""
    result = deepflatten([1, [2, [3, 4]], 5], depth=1, types=(list,))
    assert list(result) == [1, 2, [3, 4], 5]


def test_deepflatten_types():
    """Ensure deepflatten types filter works"""
    result = deepflatten(
        [1, [2, 3], 4, {"key": ["val1", "val2"]}], depth=1, types=(list,)
    )
    assert list(result) == [1, 2, 3, 4, {"key": ["val1", "val2"]}]
