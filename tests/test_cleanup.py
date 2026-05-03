import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from plumbum import local

import copier

from .helpers import build_file_tree, git_save


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


@pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "`os.kill(pid, SIGINT)` is not supported on Windows; "
        "there is no clean way to deliver SIGINT to the parent process from a child."
    ),
)
def test_cleanup_on_interrupt_during_copy_task(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test cleaning up when copy is interrupted during task."""
    src, dst, tmp = map(tmp_path_factory.mktemp, ("src", "dst", "tmp"))

    # Isolate the temp root so we only see clone dirs created by this test.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    monkeypatch.setenv("TMPDIR", str(tmp))

    build_file_tree(
        {
            src / "copier.yml": (
                f"""\
                _tasks:
                    - "{{{{ _copier_python }}}} -c 'import os, signal; os.kill({os.getpid()}, signal.SIGINT)'"
                """
            ),
        }
    )
    git_save(src, tag="v1")

    with pytest.raises(KeyboardInterrupt):
        copier.run_copy(str(src), dst, unsafe=True)

    assert list(tmp.glob("**/*")) == []


@pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "`os.kill(pid, SIGINT)` is not supported on Windows; "
        "there is no clean way to deliver SIGINT to the parent process from a child."
    ),
)
def test_cleanup_on_interrupt_during_update_task(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test cleaning up when update is interrupted during task."""
    src, dst, tmp = map(tmp_path_factory.mktemp, ("src", "dst", "tmp"))

    # Isolate the temp root so we only see clone dirs created by this test.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    monkeypatch.setenv("TMPDIR", str(tmp))

    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_yaml }}"
            ),
        }
    )
    git_save(src, tag="v1")

    build_file_tree(
        {
            src / "copier.yml": (
                f"""\
                _tasks:
                    - "{{{{ _copier_python }}}} -c 'import os, signal; os.kill({os.getpid()}, signal.SIGINT)'"
                """
            ),
        }
    )
    git_save(src, tag="v2")

    copier.run_copy(str(src), dst, vcs_ref="v1")
    git_save(dst)

    with pytest.raises(KeyboardInterrupt):
        copier.run_update(dst, overwrite=True, unsafe=True)

    assert list(tmp.glob("**/*")) == []


def test_cleanup_on_interrupt_during_git_clone(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test cleaning up when copy is interrupted during git clone."""
    src, dst, tmp = map(tmp_path_factory.mktemp, ("src", "dst", "tmp"))

    # Isolate the temp root so we only see clone dirs created by this test.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    monkeypatch.setenv("TMPDIR", str(tmp))

    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_yaml }}"
            ),
        }
    )
    git_save(src, tag="v1")

    original_popen = subprocess.Popen

    def interrupting_popen(args, *a, **kw):  # type: ignore[no-untyped-def]
        cmd_list = list(args) if isinstance(args, (list, tuple)) else [args]
        is_git_clone = (
            len(cmd_list) >= 2
            and Path(str(cmd_list[0])).stem == "git"
            and "clone" in cmd_list
        )
        if is_git_clone:
            # `signal.raise_signal` works on both POSIX and Windows, whereas
            # `os.kill(os.getpid(), SIGINT)` would terminate the process on Windows
            # instead of raising `KeyboardInterrupt`.
            signal.raise_signal(signal.SIGINT)
        return original_popen(args, *a, **kw)

    # `plumbum.machines.local` executes `from subprocess import Popen` at import
    # time, this is what we need to patch, but this module actually returns a
    # `LocalMachine` instance via plumbum's module-replacement magic. The real module
    # is accessible via `sys.modules`.
    import plumbum.machines.local  # noqa: F401  (ensure module is loaded into sys.modules)

    monkeypatch.setattr(
        sys.modules["plumbum.machines.local"], "Popen", interrupting_popen
    )

    with pytest.raises(KeyboardInterrupt):
        copier.run_copy(str(src), dst)

    assert list(tmp.glob("**/*")) == []
