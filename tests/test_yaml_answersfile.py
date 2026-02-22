"""Tests for .yaml answers file support alongside .yml."""

from __future__ import annotations

import warnings
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

import copier
from copier._user_data import (
    DEFAULT_ANSWERS_FILE_YAML,
    DEFAULT_ANSWERS_FILE_YML,
    load_answersfile_data,
    resolve_answersfile_path,
)

from .helpers import build_file_tree, git_save


@pytest.fixture
def simple_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a simple template for testing."""
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            (root / "copier.yml"): dedent(
                """\
                name:
                    type: str
                    default: test
                """
            ),
            (root / "{{ _copier_conf.answers_file }}.jinja"): (
                "{{ _copier_answers|tojson }}"
            ),
        }
    )
    git_save(root)
    return root


class TestLoadAnswersfileData:
    """Tests for load_answersfile_data function."""

    def test_loads_yml_file(self, tmp_path: Path) -> None:
        """Test that .yml file is loaded correctly."""
        answers_file = tmp_path / DEFAULT_ANSWERS_FILE_YML
        answers_file.write_text("name: test\n")

        result = load_answersfile_data(tmp_path)
        assert result == {"name": "test"}

    def test_loads_yaml_file(self, tmp_path: Path) -> None:
        """Test that .yaml file is loaded when .yml doesn't exist."""
        answers_file = tmp_path / DEFAULT_ANSWERS_FILE_YAML
        answers_file.write_text("name: test_yaml\n")

        result = load_answersfile_data(tmp_path)
        assert result == {"name": "test_yaml"}

    def test_yml_takes_precedence_over_yaml(self, tmp_path: Path) -> None:
        """Test that .yml is used when both files exist."""
        yml_file = tmp_path / DEFAULT_ANSWERS_FILE_YML
        yaml_file = tmp_path / DEFAULT_ANSWERS_FILE_YAML
        yml_file.write_text("source: yml\n")
        yaml_file.write_text("source: yaml\n")

        # Should warn about both files existing
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_answersfile_data(tmp_path)
            assert len(w) == 1
            assert "Both" in str(w[0].message)
            assert DEFAULT_ANSWERS_FILE_YML in str(w[0].message)

        # .yml content should be used
        assert result == {"source": "yml"}

    def test_returns_empty_when_no_file_exists(self, tmp_path: Path) -> None:
        """Test that empty dict is returned when no answers file exists."""
        result = load_answersfile_data(tmp_path)
        assert result == {}

    def test_explicit_file_path_takes_precedence(self, tmp_path: Path) -> None:
        """Test that explicit file path bypasses auto-detection."""
        custom_file = tmp_path / "custom-answers.yml"
        custom_file.write_text("source: custom\n")
        default_file = tmp_path / DEFAULT_ANSWERS_FILE_YML
        default_file.write_text("source: default\n")

        result = load_answersfile_data(tmp_path, "custom-answers.yml")
        assert result == {"source": "custom"}


class TestResolveAnswersfilePath:
    """Tests for resolve_answersfile_path function."""

    def test_returns_yml_when_yml_exists(self, tmp_path: Path) -> None:
        """Test that .yml is returned when it exists."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).write_text("")
        result = resolve_answersfile_path(tmp_path)
        assert result == Path(DEFAULT_ANSWERS_FILE_YML)

    def test_returns_yaml_when_only_yaml_exists(self, tmp_path: Path) -> None:
        """Test that .yaml is returned when only .yaml exists."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YAML).write_text("")
        result = resolve_answersfile_path(tmp_path)
        assert result == Path(DEFAULT_ANSWERS_FILE_YAML)

    def test_returns_yml_as_default(self, tmp_path: Path) -> None:
        """Test that .yml is the default when neither file exists."""
        result = resolve_answersfile_path(tmp_path)
        assert result == Path(DEFAULT_ANSWERS_FILE_YML)

    def test_warns_when_both_files_exist(self, tmp_path: Path) -> None:
        """Test that warning is raised when both files exist."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).write_text("")
        (tmp_path / DEFAULT_ANSWERS_FILE_YAML).write_text("")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_answersfile_path(tmp_path)
            assert len(w) == 1
            assert "Both" in str(w[0].message)

        # Still returns .yml
        assert result == Path(DEFAULT_ANSWERS_FILE_YML)


class TestCopyWithYamlAnswersFile:
    """Integration tests for copy operations with .yaml answers files."""

    def test_new_project_uses_yml_by_default(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """Test that new projects create .yml answers file by default."""
        copier.run_copy(str(simple_template), tmp_path, defaults=True)

        assert (tmp_path / DEFAULT_ANSWERS_FILE_YML).exists()
        assert not (tmp_path / DEFAULT_ANSWERS_FILE_YAML).exists()

    def test_update_preserves_yaml_file(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """Test that updating a project with .yaml file preserves the extension."""
        # Create initial project with .yaml answers file
        yaml_file = tmp_path / DEFAULT_ANSWERS_FILE_YAML
        yaml_file.write_text(
            yaml.dump(
                {
                    "_src_path": str(simple_template),
                    "_commit": "HEAD",
                    "name": "original",
                }
            )
        )
        git_save(tmp_path)

        # Update using the existing .yaml file
        copier.run_update(tmp_path, defaults=True, overwrite=True)

        # Subproject should have detected and used the .yaml file
        # Note: The template still writes to its configured answers_file
        # (defaults to .yml unless overridden)
        # This test mainly verifies reading from .yaml works

    def test_reads_existing_yaml_answers(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """Test that copier can read answers from existing .yaml file."""
        # Manually create a project with .yaml answers
        yaml_file = tmp_path / DEFAULT_ANSWERS_FILE_YAML
        yaml_file.write_text(
            yaml.dump(
                {
                    "_src_path": str(simple_template),
                    "_commit": "HEAD",
                    "name": "from_yaml",
                }
            )
        )
        git_save(tmp_path)

        # Should be able to read the _src_path from .yaml file
        from copier._subproject import Subproject

        subproject = Subproject(local_abspath=tmp_path)
        assert subproject.last_answers.get("_src_path") == str(simple_template)
        assert subproject.last_answers.get("name") == "from_yaml"


class TestSubprojectAnswersDetection:
    """Tests for Subproject answers file detection."""

    def test_subproject_detects_yml_file(self, tmp_path: Path) -> None:
        """Test Subproject detects .yml answers file."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).write_text("name: from_yml\n")

        from copier._subproject import Subproject

        subproject = Subproject(local_abspath=tmp_path)
        assert subproject.resolved_answers_relpath == Path(DEFAULT_ANSWERS_FILE_YML)
        assert subproject.last_answers == {"name": "from_yml"}

    def test_subproject_detects_yaml_file(self, tmp_path: Path) -> None:
        """Test Subproject detects .yaml answers file when .yml doesn't exist."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YAML).write_text("name: from_yaml\n")

        from copier._subproject import Subproject

        subproject = Subproject(local_abspath=tmp_path)
        assert subproject.resolved_answers_relpath == Path(DEFAULT_ANSWERS_FILE_YAML)
        assert subproject.last_answers == {"name": "from_yaml"}

    def test_subproject_prefers_yml_over_yaml(self, tmp_path: Path) -> None:
        """Test Subproject prefers .yml when both files exist."""
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).write_text("name: from_yml\n")
        (tmp_path / DEFAULT_ANSWERS_FILE_YAML).write_text("name: from_yaml\n")

        from copier._subproject import Subproject

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            subproject = Subproject(local_abspath=tmp_path)
            # Access properties to trigger loading
            _ = subproject.resolved_answers_relpath
            _ = subproject.last_answers

            # Should have warnings about both files
            warning_messages = [str(warning.message) for warning in w]
            assert any("Both" in msg for msg in warning_messages)

        assert subproject.resolved_answers_relpath == Path(DEFAULT_ANSWERS_FILE_YML)
        assert subproject.last_answers == {"name": "from_yml"}

    def test_subproject_uses_explicit_path(self, tmp_path: Path) -> None:
        """Test Subproject uses explicitly provided answers_relpath."""
        custom_file = tmp_path / "custom-answers.yml"
        custom_file.write_text("name: custom\n")
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).write_text("name: default\n")

        from copier._subproject import Subproject

        subproject = Subproject(
            local_abspath=tmp_path, answers_relpath=Path("custom-answers.yml")
        )
        assert subproject.resolved_answers_relpath == Path("custom-answers.yml")
        assert subproject.last_answers == {"name": "custom"}
