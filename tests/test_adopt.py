"""Tests for the `copier adopt` command."""

from pathlib import Path

import pytest
from plumbum import local

from copier import run_adopt
from copier._cli import CopierApp
from copier._user_data import load_answersfile_data

from .helpers import build_file_tree, git_save


@pytest.fixture(scope="module")
def tpl(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A simple template for testing adopt."""
    dst = tmp_path_factory.mktemp("tpl")
    with local.cwd(dst):
        build_file_tree(
            {
                "copier.yml": "your_name: Mario",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
                "name.txt.jinja": "This is your name: {{ your_name }}.",
                "new_file.txt": "This file is new from template.",
            }
        )
        git_save()
    return str(dst)


def test_adopt_creates_new_files(tpl: str, tmp_path: Path) -> None:
    """Test that adopt creates files that don't exist in the project."""
    # Create an existing project (not from copier)
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "existing.txt": "This file already exists.",
            }
        )
        git_save()

    # Adopt the template
    run_adopt(tpl, tmp_path, data={"your_name": "Luigi"}, defaults=True)

    # New files should be created
    assert (tmp_path / "name.txt").exists()
    assert (tmp_path / "name.txt").read_text() == "This is your name: Luigi."
    assert (tmp_path / "new_file.txt").exists()
    assert (tmp_path / "new_file.txt").read_text() == "This file is new from template."
    # Existing file should still exist
    assert (tmp_path / "existing.txt").read_text() == "This file already exists."


def test_adopt_creates_answers_file(tpl: str, tmp_path: Path) -> None:
    """Test that adopt creates a valid .copier-answers.yml file."""
    # Create an existing project
    with local.cwd(tmp_path):
        build_file_tree({"existing.txt": "exists"})
        git_save()

    # Adopt the template
    run_adopt(tpl, tmp_path, data={"your_name": "Peach"}, defaults=True)

    # Answers file should exist and contain correct data
    answers = load_answersfile_data(tmp_path)
    assert answers["your_name"] == "Peach"
    assert "_commit" in answers or "_src_path" in answers


def test_adopt_merges_conflicting_files(tpl: str, tmp_path: Path) -> None:
    """Test that adopt creates conflict markers for differing files."""
    # Create an existing project with a file that will conflict
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "name.txt": "My custom name file content.",
            }
        )
        git_save()

    # Adopt the template
    run_adopt(tpl, tmp_path, data={"your_name": "Toad"}, defaults=True)

    # The file should have conflict markers
    content = (tmp_path / "name.txt").read_text()
    assert "<<<<<<< existing" in content
    assert "=======" in content
    assert ">>>>>>> template" in content
    assert "My custom name file content." in content
    assert "This is your name: Toad." in content


def test_adopt_skips_identical_files(tpl: str, tmp_path: Path) -> None:
    """Test that adopt skips files that are identical."""
    # Create an existing project with identical content
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "new_file.txt": "This file is new from template.",
            }
        )
        git_save()

    # Adopt the template
    run_adopt(tpl, tmp_path, data={"your_name": "Yoshi"}, defaults=True)

    # The file should be unchanged (no conflict markers)
    content = (tmp_path / "new_file.txt").read_text()
    assert content == "This file is new from template."
    assert "<<<<<<" not in content


def test_adopt_cli(tpl: str, tmp_path: Path) -> None:
    """Test adopt via CLI."""
    # Create an existing project
    with local.cwd(tmp_path):
        build_file_tree({"existing.txt": "exists"})
        git_save()

    # Run adopt via CLI
    _, retcode = CopierApp.run(
        ["copier", "adopt", "-l", "-d", "your_name=Bowser", tpl, str(tmp_path)],
        exit=False,
    )
    assert retcode == 0

    # Verify results
    assert (tmp_path / "name.txt").read_text() == "This is your name: Bowser."
    answers = load_answersfile_data(tmp_path)
    assert answers["your_name"] == "Bowser"


def test_adopt_with_rej_conflict_mode(tpl: str, tmp_path: Path) -> None:
    """Test adopt with --conflict=rej creates .rej files."""
    # Create an existing project with a conflicting file
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "name.txt": "My custom content.",
            }
        )
        git_save()

    # Adopt with rej mode
    run_adopt(tpl, tmp_path, data={"your_name": "Wario"}, defaults=True, conflict="rej")

    # Original file should be unchanged
    assert (tmp_path / "name.txt").read_text() == "My custom content."
    # Rej file should contain template version
    assert (tmp_path / "name.txt.rej").exists()
    assert "This is your name: Wario." in (tmp_path / "name.txt.rej").read_text()


def test_adopt_enables_future_updates(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that after adopt, copier update works correctly."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template v1
    build_file_tree(
        {
            src / "copier.yml": "name: default",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "file.txt.jinja": "v1: {{ name }}",
        }
    )
    git_save(src, tag="v1")

    # Create existing project (not from copier)
    build_file_tree({dst / "existing.txt": "my file"})
    git_save(dst)

    # Adopt v1
    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)
    git_save(dst)

    assert (dst / "file.txt").read_text() == "v1: test"
    answers = load_answersfile_data(dst)
    assert answers["name"] == "test"
    assert "_commit" in answers


def test_adopt_binary_files_use_rej(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test that binary files with conflicts create .rej files instead of inline markers."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template with binary file (contains null bytes)
    build_file_tree(
        {
            src / "copier.yml": "name: test",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "image.bin": b"\x89PNG\r\n\x1a\n\x00\x00\x00template",
        }
    )
    git_save(src)

    # Create existing project with different binary file
    build_file_tree(
        {
            dst / "image.bin": b"\x89PNG\r\n\x1a\n\x00\x00\x00existing",
        }
    )
    git_save(dst)

    # Adopt (default is inline mode, but binary should use rej)
    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)

    # Original file should be unchanged (no corruption from conflict markers)
    original = (dst / "image.bin").read_bytes()
    assert b"\x00" in original  # Still binary
    assert b"<<<<<<<" not in original  # No conflict markers

    # Rej file should exist with template version
    assert (dst / "image.bin.rej").exists()
    rej_content = (dst / "image.bin.rej").read_bytes()
    assert b"template" in rej_content


def test_adopt_respects_skip_if_exists(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that adopt skips files matching _skip_if_exists when they already exist."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template with _skip_if_exists
    build_file_tree(
        {
            src / "copier.yml": (
                "_skip_if_exists:\n  - existing.txt\n  - config/*\nname: test"
            ),
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "existing.txt": "template version",
            src / "new.txt": "new file",
            src / "config" / "settings.yml": "template settings",
        }
    )
    git_save(src)

    # Create existing project with files that match _skip_if_exists
    build_file_tree(
        {
            dst / "existing.txt": "my custom content - should NOT be touched",
            dst
            / "config"
            / "settings.yml": "my custom settings - should NOT be touched",
        }
    )
    git_save(dst)

    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)

    # Files matching _skip_if_exists should be SKIPPED (not merged, not overwritten)
    assert (
        dst / "existing.txt"
    ).read_text() == "my custom content - should NOT be touched"
    assert (
        dst / "config" / "settings.yml"
    ).read_text() == "my custom settings - should NOT be touched"
    # No conflict markers
    assert "<<<<<<" not in (dst / "existing.txt").read_text()
    # New file should still be created
    assert (dst / "new.txt").read_text() == "new file"


def test_adopt_respects_exclude(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test that adopt respects exclude patterns."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template with exclude pattern
    build_file_tree(
        {
            src / "copier.yml": "_exclude:\n  - '*.secret'\nname: test",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "normal.txt": "normal file",
            src / "secret.secret": "should be excluded",
        }
    )
    git_save(src)

    # Create existing project
    build_file_tree({dst / "existing.txt": "exists"})
    git_save(dst)

    # Adopt
    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)

    # Normal file should be created, secret file should be excluded
    assert (dst / "normal.txt").exists()
    assert not (dst / "secret.secret").exists()


def test_adopt_pretend_mode(tpl: str, tmp_path: Path) -> None:
    """Test that adopt with pretend=True makes no changes."""
    # Create an existing project
    with local.cwd(tmp_path):
        build_file_tree({"existing.txt": "exists"})
        git_save()

    original_files = set(tmp_path.iterdir())

    # Adopt with pretend mode
    run_adopt(tpl, tmp_path, data={"your_name": "DK"}, defaults=True, pretend=True)

    # No new files should be created
    assert set(tmp_path.iterdir()) == original_files
    assert not (tmp_path / "name.txt").exists()
    assert not (tmp_path / ".copier-answers.yml").exists()


def test_adopt_non_git_destination(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test that adopt works on non-git destination projects."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template (must be git repo)
    build_file_tree(
        {
            src / "copier.yml": "name: test",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "file.txt": "template content",
        }
    )
    git_save(src)

    # Create existing project WITHOUT git init
    build_file_tree({dst / "existing.txt": "exists"})
    # No git_save() - destination is not a git repo

    # Adopt should still work
    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)

    assert (dst / "file.txt").exists()
    assert (dst / ".copier-answers.yml").exists()


def test_adopt_deep_nested_directories(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that adopt handles deeply nested directory structures."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template with deep nesting
    build_file_tree(
        {
            src / "copier.yml": "name: test",
            src / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "a" / "b" / "c" / "d" / "deep.txt": "deep content",
        }
    )
    git_save(src)

    # Create existing project with conflicting deep file
    build_file_tree(
        {
            dst / "a" / "b" / "c" / "d" / "deep.txt": "existing deep content",
        }
    )
    git_save(dst)

    run_adopt(str(src), dst, data={"name": "test"}, defaults=True)

    # Deep file should have conflict markers
    content = (dst / "a" / "b" / "c" / "d" / "deep.txt").read_text()
    assert "<<<<<<< existing" in content
    assert "deep content" in content
    assert "existing deep content" in content


def test_adopt_with_subdirectory(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test that adopt works with templates using _subdirectory."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # Create template with _subdirectory
    build_file_tree(
        {
            src / "copier.yml": "_subdirectory: project\nname: test",
            src / "project" / "{{ _copier_conf.answers_file }}.jinja": (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            src / "project" / "file.txt.jinja": "Hello {{ name }}",
        }
    )
    git_save(src)

    # Create existing project
    build_file_tree({dst / "existing.txt": "exists"})
    git_save(dst)

    run_adopt(str(src), dst, data={"name": "world"}, defaults=True)

    # File should be rendered from subdirectory
    assert (dst / "file.txt").exists()
    assert (dst / "file.txt").read_text() == "Hello world"
    # copier.yml should NOT be in destination (it's outside subdirectory)
    assert not (dst / "copier.yml").exists()
