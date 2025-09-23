from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable

import pytest
import yaml
from plumbum import local
from pydantic import ValidationError

import copier
from copier._main import Worker
from copier._template import (
    DEFAULT_EXCLUDE,
    Task,
    Template,
    apply_condition,
    condition_include,
    condition_questions,
    condition_settings,
    get_include_file_N_condition,
    jinja_str_to_f_str,
    load_template_config,
    transform_jinja_cond_to_jinja_var,
    trim_cond,
)
from copier._types import AnyByStrDict
from copier.errors import InvalidConfigFileError, MultipleConfigFilesError

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree, git_init

GOOD_ENV_OPS = {
    "autoescape": True,
    "block_start_string": "<%",
    "block_end_string": "%>",
    "variable_start_string": "<<",
    "variable_end_string": ">>",
    "keep_trailing_newline": False,
    "i_am_not_a_member": None,
    "comment_end_string": "#>",
    "comment_start_string": "<#",
}


def test_config_data_is_loaded_from_file() -> None:
    tpl = Template("tests/demo_data")
    assert tpl.exclude == ("exclude1", "exclude2")
    assert tpl.skip_if_exists == ["skip_if_exists1", "skip_if_exists2"]
    assert tpl.tasks == [
        Task(cmd="touch 1", extra_vars={"stage": "task"}),
        Task(cmd="touch 2", extra_vars={"stage": "task"}),
    ]


def test_config_data_is_merged_from_files() -> None:
    tpl = Template("tests/demo_merge_options_from_answerfiles")
    assert list(tpl.skip_if_exists) == [
        "skip_if_exists0",
        "skip_if_exists1",
        "skip_if_exists2",
    ]
    assert list(tpl.exclude) == ["exclude1", "exclude21", "exclude22"]
    assert list(tpl.jinja_extensions) == ["jinja2.ext.0", "jinja2.ext.2"]
    assert list(tpl.secret_questions) == ["question1"]


@pytest.mark.parametrize("config_suffix", ["yaml", "yml"])
def test_read_data(
    tmp_path_factory: pytest.TempPathFactory, config_suffix: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / f"copier.{config_suffix}"): (
                f"""\
                # This is a comment
                _envops: {BRACKET_ENVOPS_JSON}
                a_string: lorem ipsum
                a_number: 12345
                a_boolean: true
                a_list:
                    - one
                    - two
                    - three
                """
            ),
            (src / "user_data.txt.jinja"): (
                """\
                A string: [[ a_string ]]
                A number: [[ a_number ]]
                A boolean: [[ a_boolean ]]
                A list: [[ ", ".join(a_list) ]]
                """
            ),
        }
    )
    copier.run_copy(str(src), dst, defaults=True, overwrite=True)
    assert (dst / "user_data.txt").read_text() == dedent(
        """\
        A string: lorem ipsum
        A number: 12345
        A boolean: True
        A list: one, two, three
        """
    )


def test_settings_defaults_precedence(
    tmp_path_factory: pytest.TempPathFactory, settings_path: Path
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                # This is a comment
                _envops: {BRACKET_ENVOPS_JSON}
                a_string: lorem ipsum
                a_number: 12345
                a_boolean: true
                a_list:
                    - one
                    - two
                    - three
                """
            ),
            (src / "user_data.txt.jinja"): (
                """\
                A string: [[ a_string ]]
                A number: [[ a_number ]]
                A boolean: [[ a_boolean ]]
                A list: [[ ", ".join(a_list) ]]
                """
            ),
        }
    )
    settings_path.write_text(
        dedent(
            """\
        defaults:
            a_string: whatever
            a_number: 42
            a_boolean: false
            a_list:
                - one
                - two
    """
        )
    )
    copier.run_copy(str(src), dst, defaults=True, overwrite=True)
    assert (dst / "user_data.txt").read_text() == dedent(
        """\
        A string: whatever
        A number: 42
        A boolean: False
        A list: one, two
        """
    )


def test_invalid_yaml(capsys: pytest.CaptureFixture[str]) -> None:
    conf_path = Path("tests", "demo_invalid", "copier.yml")
    with pytest.raises(InvalidConfigFileError):
        load_template_config(conf_path)
    _, err = capsys.readouterr()
    assert "INVALID CONFIG FILE" in err
    assert str(conf_path) in err


@pytest.mark.parametrize(
    "conf_path, check_err",
    [
        ("tests/demo_invalid", lambda x: "INVALID" in x),
        # test key collision between including and included file
        ("tests/demo_transclude_invalid/demo", None),
        # test key collision between two included files
        ("tests/demo_transclude_invalid_multi/demo", None),
    ],
)
def test_invalid_config_data(
    capsys: pytest.CaptureFixture[str],
    conf_path: str,
    check_err: Callable[[str], bool] | None,
) -> None:
    template = Template(conf_path)
    with pytest.raises(InvalidConfigFileError):
        template.config_data  # noqa: B018
    if check_err:
        _, err = capsys.readouterr()
        assert check_err(err)


def test_valid_multi_section(tmp_path: Path) -> None:
    """Including multiple files works fine merged with multiple sections."""
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "exclusions.yml": "_exclude: ['*.yml']",
                "common_jinja.yml": (
                    f"""\
                    _templates_suffix: {SUFFIX_TMPL}
                    _envops:
                        block_start_string: "[%"
                        block_end_string: "%]"
                        comment_start_string: "[#"
                        comment_end_string: "#]"
                        variable_start_string: "[["
                        variable_end_string: "]]"
                        keep_trailing_newline: true
                    """
                ),
                "common_questions.yml": (
                    """\
                    your_age:
                        type: int
                    your_name:
                        type: yaml
                        help: your name from common questions
                    """
                ),
                "copier.yml": (
                    """\
                    ---
                    !include 'common_*.yml'
                    ---
                    !include exclusions.yml
                    ---
                    your_name:
                        type: str
                        help: your name from latest section
                    """
                ),
            }
        )
    template = Template(str(tmp_path))
    assert template.exclude == ("*.yml",)
    assert template.envops == {
        "block_end_string": "%]",
        "block_start_string": "[%",
        "comment_end_string": "#]",
        "comment_start_string": "[#",
        "keep_trailing_newline": True,
        "variable_end_string": "]]",
        "variable_start_string": "[[",
    }
    assert template.questions_data == {
        "your_age": {"type": "int"},
        "your_name": {"type": "str", "help": "your name from latest section"},
    }


def test_empty_section(tmp_path: Path) -> None:
    """Empty sections are ignored."""
    build_file_tree(
        {
            (tmp_path / "copier.yml"): (
                """\
                ---
                ---

                ---
                your_age:
                    type: int
                your_name:
                    type: str
                ---
                """
            ),
        }
    )
    template = Template(str(tmp_path))
    assert template.questions_data == {
        "your_age": {"type": "int"},
        "your_name": {"type": "str"},
    }


def test_include_path_must_be_relative(tmp_path: Path) -> None:
    """Include path must not be a relative path."""
    build_file_tree(
        {
            (tmp_path / "copier.yml"): (
                """\
                !include /absolute/path/to/common.yml
                """
            ),
        }
    )
    template = Template(str(tmp_path))
    with pytest.raises(
        ValueError, match="YAML include file path must be a relative path"
    ):
        template.config_data  # noqa: B018


@pytest.mark.parametrize("include_value", ["[]", "{}"])
def test_include_value_must_be_scalar_node(tmp_path: Path, include_value: str) -> None:
    """Include value must be a YAML scalar node."""
    build_file_tree(
        {
            (tmp_path / "copier.yml"): (
                f"""\
                !include {include_value}
                """
            ),
        }
    )
    template = Template(str(tmp_path))
    with pytest.raises(ValueError, match=r"^Unsupported YAML node:"):
        template.config_data  # noqa: B018


def test_config_data_empty() -> None:
    template = Template("tests/demo_config_empty")
    assert template.config_data == {}
    assert template.questions_data == {}


def test_multiple_config_file_error() -> None:
    template = Template("tests/demo_multi_config")
    with pytest.raises(MultipleConfigFilesError):
        template.config_data  # noqa: B018


# ConfigData
@pytest.mark.parametrize(
    "data",
    (
        {"pretend": "not_a_bool"},
        {"quiet": "not_a_bool"},
        {"overwrite": "not_a_bool"},
        {"cleanup_on_error": "not_a_bool"},
        {"overwrite": True, "skip_if_exists": True},
    ),
)
def test_flags_bad_data(data: AnyByStrDict) -> None:
    with pytest.raises(ValidationError):
        Worker(**data)


def test_flags_extra_fails() -> None:
    with pytest.raises(ValidationError):
        Worker(  # type: ignore[call-arg]
            src_path="..",
            dst_path=Path(),
            i_am_not_a_member="and_i_do_not_belong_here",
        )


def test_missing_template(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        copier.run_copy("./i_do_not_exist", tmp_path)


def is_subdict(small: dict[Any, Any], big: dict[Any, Any]) -> bool:
    return {**big, **small} == big


def test_worker_good_data(tmp_path: Path) -> None:
    # This test is probably useless, as it tests the what and not the how
    conf = Worker("./tests/demo_data", tmp_path)
    assert conf._render_context()["_folder_name"] == tmp_path.name
    assert conf.all_exclusions == ("exclude1", "exclude2")
    assert conf.template.skip_if_exists == ["skip_if_exists1", "skip_if_exists2"]
    assert conf.template.tasks == [
        Task(cmd="touch 1", extra_vars={"stage": "task"}),
        Task(cmd="touch 2", extra_vars={"stage": "task"}),
    ]


@pytest.mark.parametrize(
    "test_input, expected_exclusions",
    [
        # func_args > defaults
        (
            {"src_path": ".", "exclude": ["aaa"]},
            tuple(DEFAULT_EXCLUDE) + ("aaa",),
        ),
        # func_args > user_data
        (
            {"src_path": "tests/demo_data", "exclude": ["aaa"]},
            ("exclude1", "exclude2", "aaa"),
        ),
    ],
)
def test_worker_config_precedence(
    tmp_path: Path, test_input: AnyByStrDict, expected_exclusions: tuple[str, ...]
) -> None:
    conf = Worker(dst_path=tmp_path, vcs_ref="HEAD", **test_input)
    assert expected_exclusions == conf.all_exclusions


def test_config_data_transclusion() -> None:
    config = Worker("tests/demo_transclude/demo")
    assert config.all_exclusions == ("exclude1", "exclude2")


def test_config_data_nested_transclusions() -> None:
    config = Worker("tests/demo_transclude_nested_include/demo")
    assert config.all_exclusions == ("exclude1", "exclude2")


@pytest.mark.parametrize(
    "user_defaults, data, expected",
    [
        # Nothing overridden.
        (
            {},
            {},
            dedent(
                """\
                A string: lorem ipsum
                A number: 12345
                A boolean: True
                A list: one, two, three
                """
            ),
        ),
        # User defaults provided.
        (
            {
                "a_string": "foo",
                "a_number": 42,
                "a_boolean": False,
                "a_list": ["four", "five", "six"],
            },
            {},
            dedent(
                """\
                A string: foo
                A number: 42
                A boolean: False
                A list: four, five, six
                """
            ),
        ),
        # User defaults + data provided.
        (
            {
                "a_string": "foo",
                "a_number": 42,
                "a_boolean": False,
                "a_list": ["four", "five", "six"],
            },
            {
                "a_string": "yosemite",
            },
            dedent(
                """\
                A string: yosemite
                A number: 42
                A boolean: False
                A list: four, five, six
                """
            ),
        ),
    ],
)
def test_user_defaults(
    tmp_path_factory: pytest.TempPathFactory,
    user_defaults: AnyByStrDict,
    data: AnyByStrDict,
    expected: str,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                a_string:
                    default: lorem ipsum
                    type: str
                a_number:
                    default: 12345
                    type: int
                a_boolean:
                    default: true
                    type: bool
                a_list:
                    default:
                        - one
                        - two
                        - three
                    type: json
                """
            ),
            (src / "user_data.txt.jinja"): (
                """\
                A string: {{ a_string }}
                A number: {{ a_number }}
                A boolean: {{ a_boolean }}
                A list: {{ ", ".join(a_list) }}
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
        }
    )
    copier.run_copy(
        str(src),
        dst,
        defaults=True,
        overwrite=True,
        user_defaults=user_defaults,
        data=data,
    )
    assert (dst / "user_data.txt").read_text() == expected


@pytest.mark.parametrize(
    (
        "user_defaults_initial",
        "user_defaults_updated",
        "data_initial",
        "data_updated",
        "settings_defaults",
        "expected_initial",
        "expected_updated",
    ),
    [
        # Initial user defaults and updated used defaults. The output
        # should remain unchanged following the update operation.
        (
            {
                "a_string": "foo",
            },
            {
                "a_string": "foobar",
            },
            {},
            {},
            {},
            dedent(
                """\
                A string: foo
                """
            ),
            dedent(
                """\
                A string: foo
                """
            ),
        ),
        # Settings defaults takes precedence over initial defaults.
        # The output should remain unchanged following the update operation.
        (
            {},
            {},
            {},
            {},
            {
                "a_string": "bar",
            },
            dedent(
                """\
                A string: bar
                """
            ),
            dedent(
                """\
                A string: bar
                """
            ),
        ),
        # User provided defaults takes precedence over initial defaults and settings defaults.
        # The output should remain unchanged following the update operation.
        (
            {
                "a_string": "foo",
            },
            {
                "a_string": "foobar",
            },
            {},
            {},
            {
                "a_string": "bar",
            },
            dedent(
                """\
                A string: foo
                """
            ),
            dedent(
                """\
                A string: foo
                """
            ),
        ),
        # User defaults + data provided. Provided data should take precedence
        # and the resulting content unchanged post-update.
        (
            {
                "a_string": "foo",
            },
            {
                "a_string": "foobar",
            },
            {
                "a_string": "yosemite",
            },
            {},
            {
                "a_string": "bar",
            },
            dedent(
                """\
                A string: yosemite
                """
            ),
            dedent(
                """\
                A string: yosemite
                """
            ),
        ),
        # User defaults + secondary defaults + data overrides. `data_updated` should
        # override user and template defaults.
        (
            {
                "a_string": "foo",
            },
            {
                "a_string": "foobar",
            },
            {
                "a_string": "yosemite",
            },
            {
                "a_string": "red rocks",
            },
            {
                "a_string": "bar",
            },
            dedent(
                """\
                A string: yosemite
                """
            ),
            dedent(
                """\
                A string: red rocks
                """
            ),
        ),
    ],
)
def test_user_defaults_updated(
    tmp_path_factory: pytest.TempPathFactory,
    user_defaults_initial: AnyByStrDict,
    user_defaults_updated: AnyByStrDict,
    data_initial: AnyByStrDict,
    data_updated: AnyByStrDict,
    settings_defaults: AnyByStrDict,
    expected_initial: str,
    expected_updated: str,
    settings_path: Path,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    with local.cwd(src):
        build_file_tree(
            {
                (src / "copier.yaml"): (
                    """\
                    a_string:
                        default: lorem ipsum
                        type: str
                    """
                ),
                (src / "user_data.txt.jinja"): (
                    """\
                    A string: {{ a_string }}
                    """
                ),
                (src / "{{ _copier_conf.answers_file }}.jinja"): (
                    """\
                    # Changes here will be overwritten by Copier
                    {{ _copier_answers|to_nice_yaml }}
                    """
                ),
            }
        )
        git_init()
    settings_path.write_text(f"defaults: {json.dumps(settings_defaults)}")

    copier.run_copy(
        str(src),
        dst,
        defaults=True,
        overwrite=True,
        user_defaults=user_defaults_initial,
        data=data_initial,
    )
    assert (dst / "user_data.txt").read_text() == expected_initial

    with local.cwd(dst):
        git_init()

    copier.run_update(
        dst,
        defaults=True,
        overwrite=True,
        user_defaults=user_defaults_updated,
        data=data_updated,
    )
    assert (dst / "user_data.txt").read_text() == expected_updated


@pytest.mark.parametrize(
    "config",
    [
        """\
        question:
            type: str
            secret: true
        """,
        """\
        question:
            type: str

        _secret_questions:
            - question
        """,
    ],
)
def test_secret_question_requires_default_value(
    tmp_path_factory: pytest.TempPathFactory, config: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "copier.yml": config})
    with pytest.raises(ValueError, match="Secret question requires a default value"):
        copier.run_copy(str(src), dst)


##### conditional_transclusion #####


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "input, output, is_error",
    (
        ("./include_me.yml when {{ var }}", ("./include_me.yml", "{{ var }}"), False),
        ("./include_me.yaml", ("./include_me.yaml", None), False),
        ("'common_*.yml'", ("'common_*.yml'", None), False),
        ("not legit", (None, None), True),
    ),
)
def test_get_include_file_N_condition(
    input: str, output: tuple[str | None, str | None], is_error: bool
) -> None:
    with pytest.raises(ValueError) if is_error else nullcontext():
        assert get_include_file_N_condition(input) == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "input, output",
    (("{{ test }}", "test"), ("test {{ ", "test "), ("}} test ", "}} test ")),
)
def test_trim_cond(input: str, output: str) -> None:
    assert trim_cond(input) == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "_dict, _condition, output",
    (
        (
            {
                "var": {"type": "int", "default": 1},
            },
            "condition",
            {
                "var": {
                    "type": "int",
                    "default": "{% if (condition) %}1{% else %}0{% endif %}",
                    "when": "{{ True if (condition) else False }}",
                },
            },
        ),
        (
            {
                "the_str": {"type": "str"},
            },
            "condition",
            {
                "the_str": {
                    "type": "str",
                    "when": "{{ True if (condition) else False }}",
                    "default": "{% if (condition) %}{% else %}{% endif %}",
                },
            },
        ),
        (
            {
                "test": {
                    "type": "{{ 'bool' if var else 'str' }}",
                    "default": "{{ '' if var else 'my_str' }}",
                },
            },
            "condition",
            {
                "test": {
                    "type": "{{ 'bool' if var else 'str' }}",
                    "default": "{% if (condition) %}{{ '' if var else 'my_str' }}{% else %}{% endif %}",
                    "when": "{{ True if (condition) else False }}",
                },
            },
        ),
        (
            {
                "_exclude": ["{% if condition %}include_me.yml{% endif %}"],
            },
            "condition",
            {
                "_exclude": ["{% if condition %}include_me.yml{% endif %}"],
            },
        ),
        # ({}, "", {}),
    ),
)
def test_condition_questions(
    _dict: dict[str, Any], _condition: str, output: dict[str, Any]
) -> None:
    condition_questions(_dict, _condition)
    assert _dict == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "input, output",
    (
        ({}, {}),
        (
            {
                "_answers_file": ".my-custom-answers.yml",
                "_external_data": {
                    "parent_tpl": "{{ parent_tpl_answers_file }}",
                    "secrets": ".secrets.yaml",
                },
                "_envops": {
                    "autoescape": "false",
                    "block_end_string": "%]",
                    "block_start_string": "[%",
                    "comment_end_string": "#]",
                    "comment_start_string": "[#",
                    "keep_trailing_newline": "true",
                    "variable_end_string": "]]",
                    "variable_start_string": "[[",
                },
                "_exclude": [
                    "include_me.yml",
                    "{% if _copier_operation == 'update' -%}src/*_example.py{% endif %}",
                    "*.bar",
                    ".git",
                ],
                "_jinja_extensions": [
                    "jinja_markdown.MarkdownExtension",
                    "jinja2_slug.SlugExtension",
                    "jinja2_time.TimeExtension",
                ],
                "_message_after_copy": 'Your project "{{ project_name }}" has been created successfully!\n\nNext steps:\n\n1. Change directory to the project root:\n\n\t$ cd {{ _copier_conf.dst_path }}\n\n2. Read "CONTRIBUTING.md" and start coding.',
                "_message_after_update": 'Your project "{{ project_name }}" has been updated successfully!\nIn case there are any conflicts, please resolve them. Then,\nyou\'re done.',
                "_message_before_copy": "Thanks for generating a project using our template.\n\nYou'll be asked a series of questions whose answers will be used to\ngenerate a tailored project for you.",
                "_message_before_update": "Thanks for updating your project using our template.\n\nYou'll be asked a series of questions whose answers are pre-populated\nwith previously entered values. Feel free to change them as needed.",
                "_migrations": [
                    "invoke -r {{ _copier_conf.src_path }} -c migrations migrate $STAGE $VERSION_FROM $VERSION_TO",
                    {
                        "version": "v1.0.0",
                        "command": "rm ./old-folder",
                        "when": "{{ _stage == 'before' }}",
                    },
                ],
                "_min_copier_version": "4.1.0",
                "_preserve_symlinks": "True",
                "_secret_questions": [
                    "password",
                ],
                "_skip_if_exists": [
                    ".secret_password.yml",
                ],
                "_skip_tasks": "{{ condition }}",
                "_subdirectory": "{{ python_engine }}",
                "_tasks": [
                    "git init",
                    "rm {{ name_of_the_project }}/README.md",
                    [
                        "invoke",
                        "--search-root={{ _copier_conf.src_path }}",
                        "after-copy",
                    ],
                    ["invoke", "end-process", "--full-conf={{ _copier_conf|to_json }}"],
                    ["{{ _copier_python }}", "task.py"],
                    {
                        "command": ["{{ _copier_python }}", "task.py"],
                        "when": "{{ _copier_operation == 'copy' }}",
                    },
                    {
                        "command": "rm {{ name_of_the_project }}/README.md",
                        "when": "{{ _copier_conf.os in  ['linux', 'macos'] }}",
                    },
                    {
                        "command": "Remove-Item {{ name_of_the_project }}\\README.md",
                        "when": "{{ _copier_conf.os == 'windows' }}",
                    },
                ],
                "_templates_suffix": ".my-custom-suffix",
            },
            ### Output ###
            {
                "_answers_file": "{% if (condition) %}.my-custom-answers.yml{% endif %}",
                "_external_data": {
                    "parent_tpl": "{% if (condition) %}{{ parent_tpl_answers_file }}{% endif %}",
                    "secrets": "{% if (condition) %}.secrets.yaml{% endif %}",
                },
                "_envops": {
                    "autoescape": "{% if (condition) %}false{% endif %}",
                    "block_end_string": "{% if (condition) %}%]{% endif %}",
                    "block_start_string": "{% if (condition) %}[%{% endif %}",
                    "comment_end_string": "{% if (condition) %}#]{% endif %}",
                    "comment_start_string": "{% if (condition) %}[#{% endif %}",
                    "keep_trailing_newline": "{% if (condition) %}true{% endif %}",
                    "variable_end_string": "{% if (condition) %}]]{% endif %}",
                    "variable_start_string": "{% if (condition) %}[[{% endif %}",
                },
                "_exclude": [
                    "{% if (condition) %}include_me.yml{% endif %}",
                    "{% if (condition) %}{% if _copier_operation == 'update' -%}src/*_example.py{% endif %}{% endif %}",
                    "{% if (condition) %}*.bar{% endif %}",
                    "{% if (condition) %}.git{% endif %}",
                ],
                "_jinja_extensions": [
                    "{% if (condition) %}jinja_markdown.MarkdownExtension{% endif %}",
                    "{% if (condition) %}jinja2_slug.SlugExtension{% endif %}",
                    "{% if (condition) %}jinja2_time.TimeExtension{% endif %}",
                ],
                "_message_after_copy": '{% if (condition) %}Your project "{{ project_name }}" has been created successfully!\n\nNext steps:\n\n1. Change directory to the project root:\n\n\t$ cd {{ _copier_conf.dst_path }}\n\n2. Read "CONTRIBUTING.md" and start coding.{% endif %}',
                "_message_after_update": '{% if (condition) %}Your project "{{ project_name }}" has been updated successfully!\nIn case there are any conflicts, please resolve them. Then,\nyou\'re done.{% endif %}',
                "_message_before_copy": "{% if (condition) %}Thanks for generating a project using our template.\n\nYou'll be asked a series of questions whose answers will be used to\ngenerate a tailored project for you.{% endif %}",
                "_message_before_update": "{% if (condition) %}Thanks for updating your project using our template.\n\nYou'll be asked a series of questions whose answers are pre-populated\nwith previously entered values. Feel free to change them as needed.{% endif %}",
                "_migrations": [
                    {
                        "command": "invoke -r {{ _copier_conf.src_path }} -c migrations migrate $STAGE $VERSION_FROM $VERSION_TO",
                        "when": "{{ condition }}",
                    },
                    {
                        "version": "v1.0.0",
                        "command": "rm ./old-folder",
                        "when": "{% if (condition) %}{{ _stage == 'before' }}{% endif %}",
                    },
                ],
                "_min_copier_version": "{% if (condition) %}4.1.0{% endif %}",
                "_preserve_symlinks": "{% if (condition) %}True{% endif %}",
                "_secret_questions": [
                    "{% if (condition) %}password{% endif %}",
                ],
                "_skip_if_exists": [
                    "{% if (condition) %}.secret_password.yml{% endif %}",
                ],
                "_skip_tasks": "{% if (condition) %}{{ condition }}{% endif %}",
                "_subdirectory": "{% if (condition) %}{{ python_engine }}{% endif %}",
                "_tasks": [
                    {"command": "git init", "when": "{{ condition }}"},
                    {
                        "command": "rm {{ name_of_the_project }}/README.md",
                        "when": "{{ condition }}",
                    },
                    {
                        "command": [
                            "invoke",
                            "--search-root={{ _copier_conf.src_path }}",
                            "after-copy",
                        ],
                        "when": "{{ condition }}",
                    },
                    {
                        "command": [
                            "invoke",
                            "end-process",
                            "--full-conf={{ _copier_conf|to_json }}",
                        ],
                        "when": "{{ condition }}",
                    },
                    {
                        "command": ["{{ _copier_python }}", "task.py"],
                        "when": "{{ condition }}",
                    },
                    {
                        "command": ["{{ _copier_python }}", "task.py"],
                        "when": "{% if (condition) %}{{ _copier_operation == 'copy' }}{% endif %}",
                    },
                    {
                        "command": "rm {{ name_of_the_project }}/README.md",
                        "when": "{% if (condition) %}{{ _copier_conf.os in  ['linux', 'macos'] }}{% endif %}",
                    },
                    {
                        "command": "Remove-Item {{ name_of_the_project }}\\README.md",
                        "when": "{% if (condition) %}{{ _copier_conf.os == 'windows' }}{% endif %}",
                    },
                ],
                "_templates_suffix": "{% if (condition) %}.my-custom-suffix{% endif %}",
            },
        ),
    ),
)
def test_condition_settings(input: dict[str, Any], output: dict[str, Any]) -> None:
    condition_settings(input, "condition")
    assert input == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "input, output",
    (
        ("{{var}}", 'f"{var}"'),
        ("Test: {{var}} number", 'f"Test: {var} number"'),
        ("Hello world!", '"Hello world!"'),
    ),
)
def test_jinja_str_to_f_str(input: str, output: str) -> None:
    assert jinja_str_to_f_str(input) == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "_cond, output",
    (
        ("{{ condition }}", "condition"),
        (
            "{% if var>0 %}Welcome {{user}}!{% else %}{% if polite %}Goodbye{% else %}Bye{% endif %}{% endif %}",
            '(f"Welcome {user}!") if (var>0) else (("Goodbye") if (polite) else ("Bye"))',
        ),
        (
            "{% if var>0 %}Welcome {{user}}!{% elif var<-2 %}Hello!{% else %}{% if polite %}Goodbye{% else %}Bye{% endif %}{% endif %}",
            '(f"Welcome {user}!") if (var>0) else ("Hello!") if (var<-2) else (("Goodbye") if (polite) else ("Bye"))',
        ),
        # ("", ""),
    ),
)
def test_transform_jinja_cond_to_jinja_var(_cond: str, output: str) -> None:
    assert transform_jinja_cond_to_jinja_var(_cond)[0] == output


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "_dict, _condition, output",
    (
        (
            {
                "var": {"type": "int", "default": 1},
            },
            "{{ condition }}",
            {
                "var": {
                    "type": "int",
                    "default": "{% if (condition) %}1{% else %}0{% endif %}",
                    "when": "{{ True if (condition) else False }}",
                },
            },
        ),
        (
            {
                "the_str": {"type": "str"},
            },
            "{{ condition }}",
            {
                "the_str": {
                    "type": "str",
                    "when": "{{ True if (condition) else False }}",
                    "default": "{% if (condition) %}{% else %}{% endif %}",
                },
            },
        ),
        (
            {
                "test": {
                    "type": "{{ 'bool' if var else 'str' }}",
                    "default": "{{ '' if var else 'my_str' }}",
                },
            },
            "{{ condition }}",
            {
                "test": {
                    "type": "{{ 'bool' if var else 'str' }}",
                    "default": "{% if (condition) %}{{ '' if var else 'my_str' }}{% else %}{% endif %}",
                    "when": "{{ True if (condition) else False }}",
                },
            },
        ),
        (
            {
                "_exclude": ["include_me.yml"],
            },
            "{{ condition }}",
            {
                "_exclude": ["{% if (condition) %}include_me.yml{% endif %}"],
            },
        ),
        (
            {
                "_exclude": ["include_me.yml"],
            },
            "{% if condition %}True{% else %}False{% endif %}",
            {
                "_exclude": [
                    '{% if (("True") if (condition) else ("False")) %}include_me.yml{% endif %}'
                ],
            },
        ),
        # ({}, "", {}),
    ),
)
def test_apply_condition(
    _dict: dict[str, Any], _condition: str, output: dict[str, Any]
) -> None:
    apply_condition(_dict, _condition)
    assert _dict == output


@pytest.mark.conditional_transclusion
def test_condition_include() -> None:
    class _Loader(yaml.FullLoader):
        """Intermediate class to avoid monkey-patching main loader."""

    conf_path = Path("./tests/demo_transclude_conditional/demo/copier.yml")
    output = {
        "_exclude": ["{% if (condition) %}include_me.yml{% endif %}"],
        "test": {
            "default": "{% if (condition) %}{{ '' if var else 'my_str' }}{% else %}{% endif %}",
            "type": "{{ 'bool' if var else 'str' }}",
            "when": "{{ True if (condition) else False }}",
        },
        "test_json": {
            "default": '{% if (condition) %}{"test":1}{% else %}{}{% endif %}',
            "type": "json",
            "when": "{{ True if (condition) else False }}",
        },
        "test_path": {
            "default": "{% if (condition) %}./tests{% else %}{% endif %}",
            "type": "path",
            "when": "{{ True if (condition) else False }}",
        },
        "test_yaml": {
            "default": "{% if (condition) %}{'test': {'type': 'bool'}}{% else %}{% endif %}",
            "type": "yaml",
            "when": "{{ True if (condition) else False }}",
        },
        "the_str": {
            "default": "{% if (condition) %}{% else %}{% endif %}",
            "type": "str",
            "when": "{{ True if (condition) else False }}",
        },
        "var": {
            "default": "{% if (condition) %}1{% else %}0{% endif %}",
            "type": "int",
            "when": "{{ True if (condition) else False }}",
        },
    }
    with conf_path.open("rb") as f:
        assert (
            condition_include(
                conf_path=conf_path,
                loader=_Loader(f),
                include_file="./include_me.yml",
                _condition="{{ condition }}",
            )
            == output
        )


@pytest.mark.conditional_transclusion
@pytest.mark.parametrize(
    "inputs, output_files, answer_file, src",
    (
        (
            {
                "condition": True,
                "var": 1,
                "the_str": "my_str",
                "test": False,
            },
            {
                ".copier-answers.yml": True,
                "test_none.py": False,
                "test.py": False,
                "test_json.py": True,
                "test_path.py": True,
                "test_yaml.py": True,
                "var.py": True,
                "copier.yml": False,
                "include_me.yml": False,
                "include_me_also.yml": False,
            },
            f"# Changes here will be overwritten by Copier\n_src_path: tests/demo_transclude_conditional/demo\ncondition: true\ntest: false\ntest_json:\n{''.join([' '] * 4)}test: 1\ntest_path: ./tests\ntest_yaml:\n{''.join([' '] * 4)}test:\n{''.join([' '] * 8)}type: bool\nthe_str: my_str\nvar: 1\n",
            "tests/demo_transclude_conditional/demo",
        ),
        (
            {
                "condition": False,
                "var": None,
                "the_str": None,
                "test": None,
            },
            {
                ".copier-answers.yml": True,
                "test_none.py": False,
                "test.py": False,
                "test_json.py": False,
                "test_path.py": False,
                "test_yaml.py": False,
                "var.py": False,
                "copier.yml": False,
                "include_me.yml": True,
                "include_me_also.yml": False,
            },
            "# Changes here will be overwritten by Copier\n_src_path: tests/demo_transclude_conditional/demo\ncondition: false\n",
            "tests/demo_transclude_conditional/demo",
        ),
        (
            {
                "condition": True,
                "var": 0,
                "the_str": "my_str",
                "test": None,
            },
            {
                ".copier-answers.yml": True,
                "test_none.py": False,
                "test.py": True,
                "test_json.py": True,
                "test_path.py": True,
                "test_yaml.py": True,
                "var.py": False,
                "copier.yml": False,
                "include_me.yml": False,
                "include_me_also.yml": False,
            },
            f"# Changes here will be overwritten by Copier\n_src_path: tests/demo_transclude_conditional/demo\ncondition: true\ntest: my_str\ntest_json:\n{''.join([' '] * 4)}test: 1\ntest_path: ./tests\ntest_yaml:\n{''.join([' '] * 4)}test:\n{''.join([' '] * 8)}type: bool\nthe_str: my_str\nvar: 0\n",
            "tests/demo_transclude_conditional/demo",
        ),
    ),
)
def test_conditional_transclusion(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    inputs: dict[str, tuple[bool, Any]],
    output_files: dict[str, bool],
    answer_file: str,
    src: str,
) -> None:
    dst = tmp_path_factory.mktemp("dst")

    # clear capture output log
    capsys.readouterr()

    # copy
    _data = {_key: _val for _key, _val in inputs.items() if _val is not None}
    print(f"{_data =}")
    copier.run_copy(
        src,
        dst,
        data=_data,
        quiet=True,
        defaults=True,
    )
    ##
    print("".join(["#"] * 20))
    print((dst / ".copier-answers.yml").read_text())
    ##
    for _key, _val in output_files.items():
        assert (dst / _key).exists() == _val, (
            f"File `{_key}` should {'' if _val else 'not'} exist."
        )
    assert (dst / ".copier-answers.yml").read_text() == answer_file
