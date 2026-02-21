"""Tests for the ignore_git_tags flag functionality.

This test suite focuses on:
1. Dual-versioning storage (both _commit and _commit_sha are stored)
2. Automatic tag resolution during updates (floating vs stable tags)
3. CLI flag and template config behavior during updates
4. End-to-end floating tag scenarios
"""

from __future__ import annotations

import pytest
import yaml
from plumbum import local

import copier
from copier import run_copy

from .helpers import build_file_tree, git


@pytest.mark.parametrize(
    "vcs_ref,ignore_git_tags",
    [
        ("v1.0.0", True),
        ("v1.0.0", False),
        ("stable/v1", True),
        ("stable/v1", False),
        ("HEAD", True),
        ("feature-branch", True),
    ],
)
def test_dual_versioning_storage(
    tmp_path_factory: pytest.TempPathFactory,
    vcs_ref: str,
    ignore_git_tags: bool,
) -> None:
    """Test that both semantic version and SHA are always stored during copy.

    This is the core dual-versioning behavior: STORAGE is independent of the flag.
    The flag only controls USAGE during updates.
    """
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

    # Create a git repo with various refs
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial commit")
        git("tag", "v1.0.0")
        git("tag", "stable/v1")
        git("checkout", "-b", "feature-branch")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with the specified ref
    run_copy(
        str(src),
        dst,
        vcs_ref=vcs_ref,
        ignore_git_tags=ignore_git_tags,
        defaults=True,
    )

    # Check that both semantic version and SHA are stored
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())

    # Both fields should be present
    assert "_commit" in answers
    assert "_commit_sha" in answers

    # SHA should be the actual commit hash
    assert answers["_commit_sha"] == commit_hash

    # _commit should be semantic (not the SHA)
    assert answers["_commit"] != commit_hash


def test_update_with_floating_tag_and_automatic_resolution(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the CORE floating tag issue: automatic tag resolution during update.

    Scenario:
    1. Create project with floating tag "stable/v1" pointing to v1.0.0
    2. Update template to v2.0.0 and move "stable/v1" tag
    3. Run copier update (VcsRef.CURRENT, no flags)
    4. Automatic resolution should detect "stable/v1" is floating
    5. Should use SHA (v1.0.0) as FROM version
    6. Should apply changes from v1.0.0 → v2.0.0
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
            (src / "README.md"): "# Version 1.0.0",
        }
    )

    # Create template at v1.0.0 with floating tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git("tag", "v1.0.0")
        git("tag", "stable/v1")  # Floating tag
        first_commit = git("rev-parse", "HEAD").strip()

    # Copy project using the floating tag
    run_copy(
        str(src),
        dst,
        vcs_ref="stable/v1",
        defaults=True,
    )

    # Verify initial state
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "stable/v1"
    assert answers["_commit_sha"] == first_commit
    assert (dst / "version.txt").read_text() == "1.0.0"

    # Initialize dst as git repo for update
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial project state")

    # Update template to v2.0.0 and MOVE the floating tag
    with local.cwd(src):
        (src / "version.txt").write_text("2.0.0")
        (src / "README.md").write_text("# Version 2.0.0")
        (src / "workflow.yml").write_text("name: ci\non: [push]")
        git("add", ".")
        git("commit", "-m", "Version 2.0.0")
        git("tag", "v2.0.0")
        git("tag", "-f", "stable/v1")  # Move floating tag to v2.0.0
        second_commit = git("rev-parse", "HEAD").strip()

    # Run update WITHOUT specifying vcs_ref (uses VcsRef.CURRENT)
    # Automatic resolution should:
    # 1. See "stable/v1" is a floating tag pattern
    # 2. Use SHA (first_commit) as FROM version
    # 3. Use current HEAD as TO version
    # 4. Calculate diff and apply changes
    copier.run_update(
        dst,
        defaults=True,
        overwrite=True,
        conflict="inline",
    )

    # Verify update worked
    updated_answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())

    # The _commit should still be "stable/v1" (semantic version preserved)
    assert updated_answers["_commit"] == "stable/v1"

    # But _commit_sha should be updated to the new commit
    assert updated_answers["_commit_sha"] == second_commit

    # Most importantly: changes should be applied
    assert (dst / "version.txt").read_text() == "2.0.0"
    assert (dst / "README.md").read_text() == "# Version 2.0.0"
    assert (dst / "workflow.yml").exists()


def test_update_with_ignore_git_tags_flag(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that --ignore-git-tags flag forces SHA usage during update.

    Even with a stable semantic version tag, the flag should force using SHA.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
        }
    )

    # Create template with semantic version tags
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git("tag", "v1.0.0")
        first_commit = git("rev-parse", "HEAD").strip()

        # Add v2.0.0
        (src / "version.txt").write_text("2.0.0")
        git("add", ".")
        git("commit", "-m", "Version 2.0.0")
        git("tag", "v2.0.0")

    # Initial copy
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        ignore_git_tags=True,
        defaults=True,
    )

    # Verify initial state
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v1.0.0"
    assert answers["_commit_sha"] == first_commit
    assert (dst / "version.txt").read_text() == "1.0.0"

    # Initialize dst as git repo
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial project state")

    # Update with --ignore-git-tags flag
    # This should force using SHA, even though v1.0.0 is a stable semver
    copier.run_update(
        dst,
        vcs_ref="v2.0.0",
        ignore_git_tags=True,
        defaults=True,
        overwrite=True,
    )

    # Verify update worked
    assert (dst / "version.txt").read_text() == "2.0.0"
    updated_answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert updated_answers["_commit"] == "v2.0.0"


def test_update_with_stable_semantic_version(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that stable semantic versions are preserved during update.

    Automatic resolution should recognize v1.0.0 as stable and allow normal updates.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): "_answers_file: .copier-answers.yml",
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
        }
    )

    # Create template with proper semantic versions
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git("tag", "v1.0.0")

        (src / "version.txt").write_text("2.0.0")
        git("add", ".")
        git("commit", "-m", "Version 2.0.0")
        git("tag", "v2.0.0")

    # Initial copy with stable semver
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        defaults=True,
    )

    # Initialize dst as git repo
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial project state")

    # Update WITHOUT flags (VcsRef.CURRENT)
    # Automatic resolution should see v1.0.0 is stable and use it normally
    copier.run_update(
        dst,
        vcs_ref="v2.0.0",
        defaults=True,
        overwrite=True,
    )

    # Verify update worked
    assert (dst / "version.txt").read_text() == "2.0.0"


def test_update_with_template_config_ignore_git_tags(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that template _ignore_git_tags config is respected during update.

    The template config should force SHA usage even without CLI flag.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                "_answers_file: .copier-answers.yml\n_ignore_git_tags: true"
            ),
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
        }
    )

    # Create template with floating tag
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git("tag", "stable/v1")
        first_commit = git("rev-parse", "HEAD").strip()

    # Copy at first commit (before tag moves)
    run_copy(
        str(src),
        dst,
        vcs_ref="stable/v1",
        ignore_git_tags=False,  # CLI flag OFF
        defaults=True,
    )

    # Verify both are stored
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "stable/v1"
    assert answers["_commit_sha"] == first_commit

    # Now update template and move the tag
    with local.cwd(src):
        (src / "version.txt").write_text("2.0.0")
        git("add", ".")
        git("commit", "-m", "Version 2.0.0")
        git("tag", "-f", "stable/v1")

    # Initialize dst as git repo
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial project state")

    # Update WITHOUT CLI flag
    # Template config (_ignore_git_tags: true) should force SHA usage
    copier.run_update(
        dst,
        defaults=True,
        overwrite=True,
    )

    # Verify update worked (template config forced SHA usage)
    assert (dst / "version.txt").read_text() == "2.0.0"


def test_cli_flag_overrides_template_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that CLI flag overrides template configuration.

    CLI --ignore-git-tags=true should override template _ignore_git_tags: false
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                "_answers_file: .copier-answers.yml\n_ignore_git_tags: false"
            ),
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
        }
    )

    # Create template
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git("tag", "v1.0.0")
        commit_hash = git("rev-parse", "HEAD").strip()

    # Copy with CLI flag=True (overrides template config=false)
    run_copy(
        str(src),
        dst,
        vcs_ref="v1.0.0",
        ignore_git_tags=True,  # Override template
        defaults=True,
    )

    # Verify dual storage
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v1.0.0"
    assert answers["_commit_sha"] == commit_hash


def test_non_git_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that ignore_git_tags has no effect on non-git templates."""
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
        ignore_git_tags=True,  # Flag is set but should have no effect
        defaults=True,
    )

    # Check that no _commit is stored (non-git template)
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert "_commit" not in answers or answers["_commit"] is None


def test_automatic_resolution_patterns(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that automatic resolution correctly identifies floating tag patterns.

    Floating patterns that should trigger SHA fallback:
    - latest
    - stable, stable/*, stable-*
    - main, master, develop, development
    - HEAD
    - Branch-like patterns (feature-*, feat/*, etc.)
    """
    floating_tags = [
        "latest",
        "stable",
        "stable/v1",
        "stable-release",
        "main",
        "master",
        "develop",
        # Note: "HEAD" is excluded because it's a reserved git reference name
        # and cannot be created as a tag. HEAD is handled by automatic resolution
        # but doesn't need a tag-based test.
        "feature-auth",
        "feat/new-feature",
    ]

    for tag in floating_tags:
        # Create fresh src and dst for each test to avoid tag conflicts
        src_test = tmp_path_factory.mktemp(f"src_{tag.replace('/', '_')}")
        dst_test = tmp_path_factory.mktemp(f"dst_{tag.replace('/', '_')}")

        build_file_tree(
            {
                (src_test / "copier.yml"): "_answers_file: .copier-answers.yml",
                (src_test / "{{_copier_conf.answers_file}}.jinja"): (
                    "{{ _copier_answers|to_nice_yaml }}"
                ),
                (src_test / "version.txt"): "1.0.0",
            }
        )

        # Create git repo with the floating tag
        with local.cwd(src_test):
            git("init")
            git("add", ".")
            git("commit", "-m", "Initial")
            git("tag", tag)

            # Update and move tag
            (src_test / "version.txt").write_text("2.0.0")
            git("add", ".")
            git("commit", "-m", "Update")
            git("tag", "-f", tag)

        # Copy using the floating tag
        run_copy(
            str(src_test),
            dst_test,
            vcs_ref=tag,
            defaults=True,
        )

        # Initialize as git repo
        with local.cwd(dst_test):
            git("init")
            git("add", ".")
            git("commit", "-m", "Initial")

        # Update - automatic resolution should use SHA
        copier.run_update(
            dst_test,
            defaults=True,
            overwrite=True,
        )

        # Verify update applied changes
        assert (dst_test / "version.txt").read_text() == "2.0.0", (
            f"Automatic resolution failed for floating tag: {tag}"
        )


def test_custom_stable_patterns_in_template_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test that custom _stable_tag_patterns from template config work.

    Template can define custom patterns for what it considers "stable".
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                "_answers_file: .copier-answers.yml\n"
                "_stable_tag_patterns:\n"
                "  - ^release/.*$\n"  # Custom: treat "release/*" as stable
            ),
            (src / "{{_copier_conf.answers_file}}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
            (src / "version.txt"): "1.0.0",
        }
    )

    # Create template with custom "stable" tag pattern
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "Version 1.0.0")
        git(
            "tag", "release/1.0.0"
        )  # Would normally be floating, but config says stable

        (src / "version.txt").write_text("2.0.0")
        git("add", ".")
        git("commit", "-m", "Version 2.0.0")
        git("tag", "release/2.0.0")

    # Copy using the custom pattern tag
    run_copy(
        str(src),
        dst,
        vcs_ref="release/1.0.0",
        defaults=True,
    )

    # Initialize as git repo
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m", "Initial")

    # Update - should treat release/1.0.0 as stable (per template config)
    copier.run_update(
        dst,
        vcs_ref="release/2.0.0",
        defaults=True,
        overwrite=True,
    )

    # Verify update worked
    assert (dst / "version.txt").read_text() == "2.0.0"
