from pathlib import Path

import pytest
from plumbum import local

import copier


def test_cleanup(tmp_path: Path) -> None:
    """Copier creates dst_path, fails to copy and removes it."""
    dst = tmp_path / "new_folder"
    with pytest.raises(copier.errors.TaskError):
        copier.run_copy("./tests/demo_cleanup", dst, quiet=True, unsafe=True)
    assert not dst.exists()


def test_do_not_cleanup(tmp_path: Path) -> None:
    """Copier creates dst_path, fails to copy and keeps it."""
    dst = tmp_path / "new_folder"
    with pytest.raises(copier.errors.TaskError):
        copier.run_copy(
            "./tests/demo_cleanup", dst, quiet=True, unsafe=True, cleanup_on_error=False
        )
    assert dst.exists()


def test_no_cleanup_when_folder_existed(tmp_path: Path) -> None:
    """Copier will not delete a folder if it didn't create it."""
    preexisting_file = tmp_path / "something"
    preexisting_file.touch()
    with pytest.raises(copier.errors.TaskError):
        copier.run_copy(
            "./tests/demo_cleanup",
            tmp_path,
            quiet=True,
            unsafe=True,
            cleanup_on_error=True,
        )
    assert tmp_path.exists()
    assert preexisting_file.exists()


def test_no_cleanup_when_template_in_parent_folder(tmp_path: Path) -> None:
    """Copier will not delete a local template in a parent folder."""
    src = tmp_path / "src"
    src.mkdir()
    dst = tmp_path / "dst"
    dst.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    with local.cwd(cwd):
        copier.run_copy(str(Path("..", "src")), dst, quiet=True)
    assert src.exists()
