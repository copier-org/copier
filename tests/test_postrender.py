"""Tests for postrender tasks."""

import platform
from pathlib import Path

import pytest

import copier

from .helpers import build_file_tree, git_save


@pytest.fixture
def template_with_postrender(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a template with postrender tasks."""
    template_path = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            template_path / "copier.yml": """\
                package:
                  type: str
                  default: boilerplate

                _postrender_tasks:
                  - "echo 'Postrender task executed' > postrender.log"
                  - command: "echo '{{ package }}' > package.txt"
                """,
            template_path / "README.md.jinja": "# Project {{ package }}",
            template_path / "src" / "main.txt.jinja": "package: {{ package }}",
        }
    )
    return template_path


def test_postrender_tasks_execute_on_copy(
    template_with_postrender: Path, tmp_path: Path
) -> None:
    """Test that postrender tasks execute during initial copy."""
    copier.run_copy(
        str(template_with_postrender),
        tmp_path,
        data={"package": "myproject"},
        defaults=True,
        unsafe=True,
    )

    # Verify postrender tasks executed
    assert (tmp_path / "postrender.log").exists()
    log_content = (tmp_path / "postrender.log").read_text().strip()
    assert "Postrender task executed" in log_content

    # Verify templated postrender task
    assert (tmp_path / "package.txt").exists()
    assert (tmp_path / "package.txt").read_text().strip() == "myproject"

    # Verify regular template rendering also worked
    assert (tmp_path / "README.md").read_text() == "# Project myproject"


def test_postrender_tasks_execute_before_regular_tasks(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """Test that postrender tasks execute before regular tasks."""
    template_path = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            template_path / "copier.yml": """\
                _postrender_tasks:
                  - "echo 'postrender' >> execution_order.log"

                _tasks:
                  - "echo 'task' >> execution_order.log"
                """,
            template_path / "README.md": "# Test",
        }
    )
    copier.run_copy(str(template_path), tmp_path, unsafe=True)

    # Verify execution order
    log = (tmp_path / "execution_order.log").read_text()
    assert log == "postrender\ntask\n"


def test_postrender_task_features(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """Test postrender task features: working_directory, when clause, and _copier_phase."""
    template_path = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            template_path / "copier.yml": """\
enable_feature:
  type: bool
  default: false

_postrender_tasks:
  # Test working_directory
  - command: "pwd > cwd.txt"
  - command: "pwd > subdir_cwd.txt"
    working_directory: ./subdir
  # Test when clause
  - command: "echo 'feature enabled' > feature.txt"
    when: "{{ enable_feature }}"
  # Test _copier_phase variable
  - command: "echo '{{ _copier_phase }}' > phase.txt"
""",
            template_path / "README.md": "# Test",
            template_path / "subdir" / ".gitkeep": "",
        }
    )

    # Test with feature disabled
    copier.run_copy(
        str(template_path),
        tmp_path,
        data={"enable_feature": False},
        unsafe=True,
    )

    # Verify working_directory
    assert (tmp_path / "cwd.txt").exists()
    assert (tmp_path / "subdir" / "subdir_cwd.txt").exists()

    # Verify when clause - feature should be disabled
    assert not (tmp_path / "feature.txt").exists()

    # Verify _copier_phase
    assert (tmp_path / "phase.txt").read_text().strip() == "postrender"

    # Test with feature enabled
    copier.run_copy(
        str(template_path),
        tmp_path,
        data={"enable_feature": True},
        unsafe=True,
        overwrite=True,
    )

    # Verify when clause - feature should now be enabled
    assert (tmp_path / "feature.txt").exists()
    assert (tmp_path / "feature.txt").read_text().strip() == "feature enabled"


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Uses Unix shell syntax",
)
def test_postrender_on_update_with_git(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """Test postrender directory renaming with mixed file types and updates.

    This test verifies:
    - Directory renaming via postrender (src/example/ -> src/{{ package }}/)
    - Mix of templated (.jinja) and non-templated files
    - New files added in template v2 end up in renamed directory
    - User files in renamed directory are preserved during update
    - Template changes are merged with user changes
    """
    template_path = tmp_path_factory.mktemp("template")

    # INITIAL TEMPLATE (v1)
    build_file_tree(
        {
            template_path / "copier.yml": """\
                _version: "1.0.0"

                package:
                  type: str
                  default: boilerplate

                _postrender_tasks:
                  # Temp directories (old_copy, new_copy): simple rename
                  - command: "[ -d src/example ] && mv src/example src/{{ package }} || true"
                    when: "{{ _update_stage in ['previous', 'new'] }}"

                  # Destination: handle both initial copy and updates
                  - command: |
                      if [ -d src/example ]; then
                        if [ ! -d "src/{{ package }}" ]; then
                          # Initial copy: simple rename
                          mv src/example "src/{{ package }}"
                        else
                          # Update: merge new template files into existing directory
                          mkdir -p "src/{{ package }}"
                          cp -R src/example/* "src/{{ package }}/"
                          rm -rf src/example
                        fi
                      fi
                    when: "{{ _update_stage == 'current' }}"
                """,
            template_path / "README.md.jinja": "# {{ package }} Project",
            template_path
            / ".copier-answers.yml.jinja": "{{ _copier_answers|to_nice_yaml }}",
            template_path / "src" / "example" / "plain.txt": "non-templated content",
            template_path
            / "src"
            / "example"
            / "file1.txt.jinja": "one {{ package }} one",
            template_path
            / "src"
            / "example"
            / "file2.txt.jinja": "two {{ package }} two",
        }
    )
    git_save(template_path, "v1.0.0", tag="1.0.0")

    # INITIAL COPY
    copier.run_copy(
        str(template_path),
        tmp_path,
        data={"package": "myproject"},
        vcs_ref="1.0.0",
        unsafe=True,
    )
    git_save(tmp_path, "Initial commit")

    # Verify initial copy: directory should be renamed
    assert not (tmp_path / "src" / "example").exists()
    assert (tmp_path / "src" / "myproject").exists()

    # Non-templated file should be copied as-is
    plain_txt = tmp_path / "src" / "myproject" / "plain.txt"
    assert plain_txt.exists()
    assert plain_txt.read_text() == "non-templated content"

    # Templated files should have rendered content
    file1 = tmp_path / "src" / "myproject" / "file1.txt"
    assert file1.exists()
    assert file1.read_text() == "one myproject one"

    file2 = tmp_path / "src" / "myproject" / "file2.txt"
    assert file2.exists()
    assert file2.read_text() == "two myproject two"

    # USER MODIFICATIONS
    build_file_tree(
        {
            tmp_path / "src" / "myproject" / "user.txt": "user custom content",
        }
    )
    # User modifies an existing template file
    file1.write_text("one myproject one\nuser added line")
    git_save(tmp_path, "User modifications")

    # UPDATE TEMPLATE (v2)
    build_file_tree(
        {
            template_path
            / "src"
            / "example"
            / "file3.txt.jinja": "three {{ package }} three",
            template_path
            / "src"
            / "example"
            / "file1.txt.jinja": "one {{ package }} one\ntemplate added line",
            template_path / "README.md.jinja": "# {{ package }} Project v2",
        }
    )
    git_save(template_path, "v2.0.0", tag="2.0.0")

    # RUN UPDATE
    copier.run_update(
        dst_path=tmp_path,
        vcs_ref="2.0.0",
        defaults=True,
        unsafe=True,
        overwrite=True,
    )

    # VERIFY UPDATE RESULTS

    # 1. Directory should still be renamed (not nested)
    assert not (tmp_path / "src" / "example").exists()
    assert (tmp_path / "src" / "myproject").exists()
    assert not (tmp_path / "src" / "myproject" / "example").exists()

    # 2. New template file should be in renamed directory
    file3 = tmp_path / "src" / "myproject" / "file3.txt"
    assert file3.exists()
    assert file3.read_text() == "three myproject three"

    # 3. User's custom file should be preserved
    user_file = tmp_path / "src" / "myproject" / "user.txt"
    assert user_file.exists()
    assert user_file.read_text() == "user custom content"

    # 4. Modified files should be merged (3-way merge)
    file1_updated = file1.read_text()
    assert "one myproject one" in file1_updated
    assert "template added line" in file1_updated
    assert "user added line" in file1_updated

    # 5. Non-templated file should still exist unchanged
    assert plain_txt.exists()
    assert plain_txt.read_text() == "non-templated content"

    # 6. Other templated files should still exist
    assert file2.exists()

    # 7. Root files should be updated
    assert (tmp_path / "README.md").read_text() == "# myproject Project v2"


def test_postrender_with_skip_tasks_flag(
    template_with_postrender: Path, tmp_path: Path
) -> None:
    """Test that skip_tasks flag also skips postrender tasks."""
    copier.run_copy(
        str(template_with_postrender),
        tmp_path,
        data={"package": "myproject"},
        skip_tasks=True,
        unsafe=True,
    )

    # Verify postrender tasks were skipped
    assert not (tmp_path / "postrender.log").exists()
    assert not (tmp_path / "package.txt").exists()

    # Verify template rendering still worked
    assert (tmp_path / "README.md").exists()


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Uses Unix shell syntax",
)
def test_postrender_conditional_on_update_stage(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """Test using _update_stage in when conditions."""
    template_path = tmp_path_factory.mktemp("template")

    (template_path / "copier.yml").write_text(
        """\
_postrender_tasks:
  - command: "echo 'expensive' > expensive.txt"
    when: "{{ _update_stage == 'current' }}"
  - command: "echo '{{ _update_stage }}' > all_stages.txt"
"""
    )
    (template_path / "README.md").write_text("# Test")

    copier.run_copy(str(template_path), tmp_path, unsafe=True)

    # Verify conditional task only ran on "current"
    assert (tmp_path / "expensive.txt").exists()
    assert (tmp_path / "expensive.txt").read_text().strip() == "expensive"

    # Verify unconditional task also ran
    assert (tmp_path / "all_stages.txt").exists()
    assert (tmp_path / "all_stages.txt").read_text().strip() == "current"
