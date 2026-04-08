from __future__ import annotations

import json

import pytest
import yaml

from copier._cli import CopierApp

from .helpers import build_file_tree


@pytest.fixture()
def template_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create a template with various question types for testing inspect."""
    root = tmp_path_factory.mktemp("inspect_template")
    build_file_tree(
        {
            (root / "copier.yaml"): """\
                project_name:
                  type: str
                  help: The name of the project

                language:
                  type: str
                  choices:
                    - python
                    - go
                    - rust

                version:
                  type: str
                  default: "1.0.0"

                add_linter:
                  type: bool
                  default: false
                  when: "{{ language == 'python' }}"
                  help: Include linter configuration?

                secret_token:
                  type: str
                  secret: true
                  help: API token for deployment

                db_connection_string:
                  type: str
                  when: false
                  default: "{{ project_name }}_db"

                computed_zero:
                  type: int
                  when: 0
                  default: 42

                tags:
                  type: yaml
                  multiselect: true
                  choices:
                    - web
                    - cli
                    - library

                license:
                  type: str
                  choices:
                    MIT License: mit
                    Apache 2.0: apache2

                dynamic_choice:
                  type: str
                  choices: "{{ available_options }}"

                count:
                  default: 42

                string_when_false:
                  type: str
                  when: "false"
                  default: "should_be_hidden"
                """,
            (root / "{{ project_name }}" / "README.md.jinja"): """\
                # {{ project_name }}
                """,
        }
    )
    return str(root)


class TestInspectPlainOutput:
    def test_shows_questions(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "project_name (str)" in out
        assert "REQUIRED" in out
        assert "language (str)" in out
        assert "version (str)" in out
        assert "default: 1.0.0" in out

    def test_shows_choices(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "choices: python, go, rust" in out

    def test_shows_when_condition(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "when: {{ language == 'python' }}" in out

    def test_shows_help_text(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "help: The name of the project" in out
        assert "help: Include linter configuration?" in out

    def test_shows_secret(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "secret: true" in out

    def test_shows_multiselect(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "multi-choices: web, cli, library" in out

    def test_shows_dict_choices(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "choices: MIT License, Apache 2.0" in out

    def test_shows_jinja_expression_choices(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "choices: {{ available_options }}" in out

    def test_infers_type_from_default(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Type is inferred from default value when not specified."""
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        assert "count (int)" in out
        assert "default: 42" in out

    def test_hides_computed_questions(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Questions with trivially false 'when' are hidden in plain output."""
        _, status = CopierApp.run(
            ["copier", "inspect", template_path], exit=False
        )
        assert status == 0
        out = capsys.readouterr().out
        # when: false (YAML bool)
        assert "db_connection_string" not in out
        # when: 0 (YAML int)
        assert "computed_zero" not in out
        # when: "false" (YAML string)
        assert "string_when_false" not in out


class TestInspectJsonOutput:
    def test_valid_json(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", "--output-format", "json", template_path],
            exit=False,
        )
        assert status == 0
        data = json.loads(capsys.readouterr().out)
        assert "project_name" in data
        assert "language" in data

    def test_includes_computed_with_marker(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Computed questions are included in JSON with computed: true."""
        _, status = CopierApp.run(
            ["copier", "inspect", "--output-format", "json", template_path],
            exit=False,
        )
        assert status == 0
        data = json.loads(capsys.readouterr().out)
        assert data["db_connection_string"]["computed"] is True
        assert data["computed_zero"]["computed"] is True
        assert data["string_when_false"]["computed"] is True
        # Non-computed questions should not have computed marker
        assert "computed" not in data["project_name"]


class TestInspectYamlOutput:
    def test_valid_yaml(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", "--output-format", "yaml", template_path],
            exit=False,
        )
        assert status == 0
        data = yaml.safe_load(capsys.readouterr().out)
        assert "project_name" in data
        assert "language" in data

    def test_includes_computed_with_marker(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", "--output-format", "yaml", template_path],
            exit=False,
        )
        assert status == 0
        data = yaml.safe_load(capsys.readouterr().out)
        assert data["db_connection_string"]["computed"] is True


class TestInspectQuiet:
    def test_suppresses_output(
        self, template_path: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", "--quiet", template_path], exit=False
        )
        assert status == 0
        captured = capsys.readouterr()
        assert captured.out == ""


class TestInspectEmptyTemplate:
    def test_no_questions(
        self, tmp_path_factory: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Template with only config (no questions) produces empty output."""
        root = tmp_path_factory.mktemp("empty_template")
        build_file_tree(
            {(root / "copier.yaml"): "_templates_suffix: .jinja\n"}
        )
        _, status = CopierApp.run(
            ["copier", "inspect", str(root)], exit=False
        )
        assert status == 0
        assert capsys.readouterr().out == ""

    def test_no_questions_json(
        self, tmp_path_factory: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = tmp_path_factory.mktemp("empty_template_json")
        build_file_tree(
            {(root / "copier.yaml"): "_templates_suffix: .jinja\n"}
        )
        _, status = CopierApp.run(
            ["copier", "inspect", "--output-format", "json", str(root)],
            exit=False,
        )
        assert status == 0
        assert json.loads(capsys.readouterr().out) == {}


class TestInspectErrors:
    def test_nonexistent_template(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, status = CopierApp.run(
            ["copier", "inspect", "/nonexistent/path"], exit=False
        )
        assert status == 1
        assert "Local template must be a directory" in capsys.readouterr().err
