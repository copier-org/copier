from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

import copier
from copier._user_data import (
    DEFAULT_ANSWERS_FILE_YAML,
    DEFAULT_ANSWERS_FILE_YML,
    load_answersfile_data,
)

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree, git_save


@pytest.fixture(scope="module")
def template_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            (root / "[[ _copier_conf.answers_file ]].tmpl"): (
                """\
                # Changes here will be overwritten by Copier
                [[ _copier_answers|to_nice_yaml ]]
                """
            ),
            (root / "copier.yml"): (
                f"""\
                _answers_file: .answers-file-changed-in-template.yml
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}

                round: 1st

                # password_1 and password_2 must not appear in answers file
                _secret_questions:
                    - password_1

                password_1: password one
                password_2:
                    secret: yes
                    default: password two
                """
            ),
            (root / "round.txt.tmpl"): (
                """\
                It's the [[round]] round.
                password_1=[[password_1]]
                password_2=[[password_2]]
                """
            ),
        }
    )
    return str(root)


@pytest.mark.parametrize("answers_file", [None, ".changed-by-user.yaml"])
def test_answersfile(
    template_path: str, tmp_path: Path, answers_file: str | None
) -> None:
    """Test copier behaves properly when using an answersfile."""
    round_file = tmp_path / "round.txt"

    # Check 1st round is properly executed and remembered
    copier.run_copy(
        template_path,
        tmp_path,
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
    )
    answers_file = answers_file or ".answers-file-changed-in-template.yml"
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 1st round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "1st"
    assert "password_1" not in log
    assert "password_2" not in log

    # Check 2nd round is properly executed and remembered
    copier.run_copy(
        template_path,
        tmp_path,
        {"round": "2nd"},
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
    )
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 2nd round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "2nd"
    assert "password_1" not in log
    assert "password_2" not in log

    # Check repeating 2nd is properly executed and remembered
    copier.run_copy(
        template_path,
        tmp_path,
        answers_file=answers_file,
        defaults=True,
        overwrite=True,
    )
    assert (
        round_file.read_text()
        == dedent(
            """
            It's the 2nd round.
            password_1=password one
            password_2=password two
            """
        ).lstrip()
    )
    log = load_answersfile_data(tmp_path, answers_file)
    assert log["round"] == "2nd"
    assert "password_1" not in log
    assert "password_2" not in log


def test_external_data(tmp_path_factory: pytest.TempPathFactory) -> None:
    parent1, parent2, child, dst = map(
        tmp_path_factory.mktemp, ("parent1", "parent2", "child", "dst")
    )
    build_file_tree(
        {
            (parent1 / "copier.yaml"): "{name: P1, child: C1}",
            (parent1 / "parent1.txt.jinja"): "{{ name }}",
            (
                parent1 / "{{ _copier_conf.answers_file }}.jinja"
            ): "{{ _copier_answers|to_nice_yaml -}}",
            (parent2 / "copier.yaml"): "name: P2",
            (parent2 / "parent2.txt.jinja"): "{{ name }}",
            (
                parent2 / "{{ _copier_conf.answers_file }}.jinja"
            ): "{{ _copier_answers|to_nice_yaml -}}",
            (child / "copier.yml"): (
                """\
                _external_data:
                    parent1: .copier-answers.yml
                    parent2: "{{ parent2_answers }}"
                parent2_answers: .parent2-answers.yml
                name: "{{ _external_data.parent2.child | d(_external_data.parent1.child) }}"
                """
            ),
            (child / "combined.json.jinja"): """\
                {
                    "parent1": {{ _external_data.parent1.name | tojson }},
                    "parent2": {{ _external_data.parent2.name | tojson }},
                    "child": {{ name | tojson }}
                }
            """,
            (
                child / "{{ _copier_conf.answers_file }}.jinja"
            ): "{{ _copier_answers|to_nice_yaml -}}",
        }
    )
    git_save(parent1, tag="v1.0+parent1")
    git_save(parent2, tag="v1.0+parent2")
    git_save(child, tag="v1.0+child")
    # Apply parent 1. At this point we don't know we'll want more than 1
    # template in the same subproject, so we leave the default answers file.
    copier.run_copy(str(parent1), dst, defaults=True, overwrite=True)
    git_save(dst)
    assert (dst / "parent1.txt").read_text() == "P1"
    expected_parent1_answers = {
        "_src_path": str(parent1),
        "_commit": "v1.0+parent1",
        "name": "P1",
        "child": "C1",
    }
    assert load_answersfile_data(dst, ".copier-answers.yml") == expected_parent1_answers
    # Apply parent 2. It uses a different answers file.
    copier.run_copy(
        str(parent2),
        dst,
        defaults=True,
        overwrite=True,
        answers_file=".parent2-answers.yml",
    )
    git_save(dst)
    assert (dst / "parent2.txt").read_text() == "P2"
    expected_parent2_answers = {
        "_commit": "v1.0+parent2",
        "_src_path": str(parent2),
        "name": "P2",
    }
    assert (
        load_answersfile_data(dst, ".parent2-answers.yml") == expected_parent2_answers
    )
    # Apply child. It can access answers from both parents.
    copier.run_copy(
        str(child),
        dst,
        defaults=True,
        overwrite=True,
        answers_file=".child-answers.yml",
    )
    git_save(dst)
    assert load_answersfile_data(dst, ".child-answers.yml") == {
        "_commit": "v1.0+child",
        "_src_path": str(child),
        "name": "C1",
        "parent2_answers": ".parent2-answers.yml",
    }
    assert json.loads((dst / "combined.json").read_text()) == {
        "parent1": "P1",
        "parent2": "P2",
        "child": "C1",
    }


def test_external_data_with_umlaut(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _external_data:
                    data: data.yml
                ext_umlaut: "{{ _external_data.data.umlaut }}"
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
        }
    )
    git_save(src, tag="v1")

    (dst / "data.yml").write_text("umlaut: äöü", encoding="utf-8")

    copier.run_copy(str(src), dst, defaults=True, overwrite=True)
    answers = load_answersfile_data(dst, ".copier-answers.yml")
    assert answers["ext_umlaut"] == "äöü"


@pytest.mark.parametrize(
    "encoding",
    ["utf-8", "utf-8-sig", "utf-16-le", "utf-16-be"],
)
def test_external_data_with_unicode_characters(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    encoding: str,
) -> None:
    def _encode(data: str) -> bytes:
        if encoding.startswith("utf-16"):
            data = f"\ufeff{data}"
        return data.encode(encoding)

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _external_data:
                    data: data.yml
                foo: "{{ _external_data.data.foo }}"
                bar: "{{ _external_data.data.bar }}"
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
        }
    )
    git_save(src, tag="v1")

    data = {
        "foo": "\u3053\u3093\u306b\u3061\u306f",  # japanese hiragana
        "bar": "\U0001f60e",  # smiling face with sunglasses
    }
    (dst / "data.yml").write_bytes(_encode(yaml.dump(data, allow_unicode=True)))

    with monkeypatch.context() as m:
        # Override the factor that determines the default encoding when opening files.
        m.setattr("io.text_encoding", lambda *_args: "cp932")
        copier.run_copy(str(src), dst, defaults=True, overwrite=True)

    answers = load_answersfile_data(dst)
    assert answers["foo"] == data["foo"]
    assert answers["bar"] == data["bar"]


def test_undefined_phase_in_external_data(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                _external_data:
                    data: '{{ _copier_phase }}.yml'
                key: "{{ _external_data.data.key }}"
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                "{{ _copier_answers|to_nice_yaml }}"
            ),
        }
    )
    git_save(src, tag="v1")

    (dst / "undefined.yml").write_text("key: value")

    copier.run_copy(str(src), dst, defaults=True, overwrite=True)
    answers = load_answersfile_data(dst, ".copier-answers.yml")
    assert answers["key"] == "value"


class TestYamlAnswersFileSuffix:
    """Tests for .yaml answers file suffix support alongside .yml."""

    @pytest.fixture
    def simple_template(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
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
        git_save(root, tag="v1")
        return root

    def test_new_project_uses_yml_by_default(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """New projects create .copier-answers.yml by default."""
        copier.run_copy(str(simple_template), tmp_path, defaults=True)
        assert (tmp_path / DEFAULT_ANSWERS_FILE_YML).exists()
        assert not (tmp_path / DEFAULT_ANSWERS_FILE_YAML).exists()

    def test_recopy_reads_yaml_answers(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """run_recopy can read answers from an existing .yaml file."""
        copier.run_copy(str(simple_template), tmp_path, defaults=True)

        # Rename .yml to .yaml to simulate a project using .yaml
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).rename(
            tmp_path / DEFAULT_ANSWERS_FILE_YAML
        )
        git_save(tmp_path)

        # run_recopy should auto-detect and read from .yaml
        copier.run_recopy(tmp_path, defaults=True, overwrite=True)

        # The template writes to .copier-answers.yml (its configured default),
        # so after recopy both may exist. Verify the recopy succeeded
        # by checking the newly written answers file is valid.
        answers = load_answersfile_data(tmp_path)
        assert answers["name"] == "test"

    def test_update_reads_yaml_answers(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """run_update can read answers from an existing .yaml file."""
        copier.run_copy(str(simple_template), tmp_path, defaults=True)

        # Rename .yml to .yaml to simulate a project using .yaml
        (tmp_path / DEFAULT_ANSWERS_FILE_YML).rename(
            tmp_path / DEFAULT_ANSWERS_FILE_YAML
        )
        git_save(tmp_path)

        # run_update should auto-detect and read from .yaml
        copier.run_update(tmp_path, defaults=True, overwrite=True)

        answers = load_answersfile_data(tmp_path)
        assert answers["name"] == "test"

    def test_yml_takes_precedence_over_yaml(
        self, simple_template: Path, tmp_path: Path
    ) -> None:
        """.yml file takes precedence when both .yml and .yaml exist."""
        copier.run_copy(
            str(simple_template), tmp_path, data={"name": "from_yml"}, defaults=True
        )

        # Create a .yaml file with different content
        yaml_file = tmp_path / DEFAULT_ANSWERS_FILE_YAML
        yml_answers = yaml.safe_load(
            (tmp_path / DEFAULT_ANSWERS_FILE_YML).read_text()
        )
        yaml_file.write_text(yaml.dump({**yml_answers, "name": "from_yaml"}))
        git_save(tmp_path)

        # recopy should use .yml (which has "from_yml"), not .yaml
        copier.run_recopy(tmp_path, defaults=True, overwrite=True)

        answers = load_answersfile_data(tmp_path)
        assert answers["name"] == "from_yml"
