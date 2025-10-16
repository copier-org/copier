"""Tests for the resolve_commit_to_sha flag functionality."""

from __future__ import annotations

import pytest
import yaml
from plumbum import local

import copier
from copier import run_copy

from .helpers import build_file_tree, git


def test_resolve_commit_to_sha_with_flag(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha flag stores SHA instead of tag."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with a tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.0.0")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with the flag enabled
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Check that SHA was stored instead of tag
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == commit_hash
    assert answers["_commit"] != "v1.0.0"


def test_resolve_commit_to_sha_without_flag(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that without the flag, the original ref is preserved."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with a tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.0.0")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy without the flag (default behavior)
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=False,
        defaults=True,
    )

    # Check that tag was preserved (git describe format)
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    # Should be v1.0.0 or git describe format like v1.0.0-0-gSHA
    assert answers["_commit"].startswith("v1.0.0")
    assert answers["_commit"] != commit_hash


def test_resolve_commit_to_sha_with_moving_tag(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha works correctly with moving tags."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "v1",
        }
    )

    # Create a git repo with a moving tag pattern
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1")
        git("tag", "stable/v1")

        # Make another commit and move the tag
        (src / "version.txt").write_text("v1.1")
        git("add", ".")
        git("commit", "-m", "Version 1.1")
        git("tag", "-f", "stable/v1")  # Move the tag
        second_commit = git("rev-parse", "HEAD").strip()

    # Copy with the flag enabled (pointing to the moved tag)
    run_copy(
        str(src),
        dst,
        vcs_ref="stable/v1",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Check that SHA was stored
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == second_commit
    assert answers["_commit"] != "stable/v1"

    # Verify the correct version was copied
    assert (dst / "version.txt").read_text() == "v1.1"


def test_resolve_commit_to_sha_with_branch(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha works with branch references."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with a branch
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("checkout", "-b", "feature-branch")
        (src / "file.txt").write_text("feature content")
        git("add", ".")
        git("commit", "-m", "Feature commit")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with the flag enabled using branch ref
    run_copy(
        str(src),
        dst,
        vcs_ref="feature-branch",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Check that SHA was stored instead of branch name
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == commit_hash
    assert answers["_commit"] != "feature-branch"


def test_resolve_commit_to_sha_with_head(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha works with HEAD reference."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with the flag enabled using HEAD ref
    run_copy(
        str(src),
        dst,
        vcs_ref="HEAD",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Check that SHA was stored
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == commit_hash


def test_resolve_commit_to_sha_non_git_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha has no effect on non-git templates."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Copy without git (local directory)
    run_copy(
        str(src),
        dst,
        resolve_commit_to_sha=True,  # Flag is set but should have no effect
        defaults=True,
    )

    # Check that no _commit is stored (non-git template)
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert "_commit" not in answers or answers["_commit"] is None


def test_resolve_commit_to_sha_with_semantic_version_tag(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that semantic version tags are preserved even with the flag."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with semantic version tags
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.2.3")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with the flag enabled but using semantic version
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.2.3",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Check that SHA was stored (since flag is enabled, it always uses SHA)
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == commit_hash


def test_resolve_commit_to_sha_update_compatibility(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that projects created with SHA can be updated properly."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "v1",
        }
    )

    # Create a git repo with tags
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1")
        git("tag", "v1.0.0")
        first_commit = git("rev-parse", "HEAD").strip()

        # Make another commit with new tag
        (src / "version.txt").write_text("v2")
        git("add", ".")
        git("commit", "-m", "Version 2")
        git("tag", "v2.0.0")

    # Initial copy with SHA resolution
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=True,
        defaults=True,
    )

    # Verify initial state
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == first_commit
    assert (dst / "version.txt").read_text() == "v1"

    # Initialize dst as a git repo for update
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial project state")

    # Update to new version (also with SHA resolution)
    copier.run_update(
        dst,
        vcs_ref="v2.0.0",
        resolve_commit_to_sha=True,
        defaults=True,
        unsafe=True,
        overwrite=True,  # Required for updates
    )

    # Verify update worked
    assert (dst / "version.txt").read_text() == "v2"


def test_resolve_commit_to_sha_from_template_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that resolve_commit_to_sha can be set in template configuration."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                "_answers_file: .copier-answers.yml\n_resolve_commit_to_sha: true"
            ),
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with a tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.0.0")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy without the CLI flag but with template config
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=False,  # CLI flag is off
        defaults=True,
    )

    # Check that SHA was stored (from template config)
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["_commit"] == commit_hash
    assert answers["_commit"] != "v1.0.0"


def test_cli_flag_overrides_template_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that CLI flag can override template configuration when set to True."""
    src, dst1, dst2 = map(tmp_path_factory.mktemp, ("src", "dst1", "dst2"))

    # Create a template that does NOT request SHA resolution
    build_file_tree(
        {
            (src / "copier.yml"): (
                "_answers_file: .copier-answers.yml\n"
                "_resolve_commit_to_sha: false"  # Template says don't use SHA
            ),
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "file.txt"): "content",
        }
    )

    # Create a git repo with a tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.0.0")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Test 1: Template says false, CLI says true (CLI should win - use SHA)
    run_copy(
        str(src),
        dst1,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=True,  # Explicitly turn on via CLI
        defaults=True,
    )

    # Check that SHA was stored (CLI overrides template config)
    answers_file1 = dst1 / ".copier-answers.yml"
    answers1 = yaml.safe_load(answers_file1.read_text())
    assert answers1["_commit"] == commit_hash
    assert answers1["_commit"] != "v1.0.0"

    # Test 2: Template says false, no CLI flag (template config should apply - no SHA)
    run_copy(
        str(src),
        dst2,
        vcs_ref="v1.0.0",
        resolve_commit_to_sha=False,  # Default - template config applies
        defaults=True,
    )

    # Check that tag was preserved (template config applies)
    answers_file2 = dst2 / ".copier-answers.yml"
    answers2 = yaml.safe_load(answers_file2.read_text())
    assert answers2["_commit"].startswith("v1.0.0")
    assert answers2["_commit"] != commit_hash
