from pathlib import Path
from textwrap import dedent

import pytest
from plumbum import local
from pydantic import ValidationError

import copier
from copier.errors import InvalidConfigFileError, MultipleConfigFilesError
from copier.template import DEFAULT_EXCLUDE, Template, load_template_config

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree

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


def test_config_data_is_loaded_from_file():
    tpl = Template("tests/demo_data")
    assert tpl.exclude == ("exclude1", "exclude2")
    assert tpl.skip_if_exists == ["skip_if_exists1", "skip_if_exists2"]
    assert tpl.tasks == ["touch 1", "touch 2"]


@pytest.mark.parametrize("config_suffix", ["yaml", "yml"])
def test_read_data(tmp_path_factory, config_suffix):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / f"copier.{config_suffix}": f"""\
                # This is a comment
                _envops: {BRACKET_ENVOPS_JSON}
                a_string: lorem ipsum
                a_number: 12345
                a_boolean: true
                a_list:
                    - one
                    - two
                    - three
            """,
            src
            / "user_data.txt.jinja": """\
                A string: [[ a_string ]]
                A number: [[ a_number ]]
                A boolean: [[ a_boolean ]]
                A list: [[ ", ".join(a_list) ]]
            """,
        }
    )
    copier.copy(str(src), dst, defaults=True, overwrite=True)
    gen_file = dst / "user_data.txt"
    result = gen_file.read_text()
    assert result == dedent(
        """\
        A string: lorem ipsum
        A number: 12345
        A boolean: True
        A list: one, two, three
        """
    )


def test_invalid_yaml(capsys):
    conf_path = Path("tests", "demo_invalid", "copier.yml")
    with pytest.raises(InvalidConfigFileError):
        load_template_config(conf_path)
    _, err = capsys.readouterr()
    assert "INVALID CONFIG FILE" in err
    assert str(conf_path) in err


@pytest.mark.parametrize(
    "conf_path,flags,check_err",
    (
        ("tests/demo_invalid", {"_warning": False}, lambda x: "INVALID" in x),
        # test key collision between including and included file
        ("tests/demo_transclude_invalid/demo", {}, None),
        # test key collision between two included files
        ("tests/demo_transclude_invalid_multi/demo", {}, None),
    ),
)
def test_invalid_config_data(conf_path, flags, check_err, capsys):
    template = Template(conf_path)
    with pytest.raises(InvalidConfigFileError):
        template.config_data
    if check_err:
        _, err = capsys.readouterr()
        assert check_err(err)


def test_valid_multi_section(tmp_path):
    """Including multiple files works fine merged with multiple sections."""
    with local.cwd(tmp_path):
        build_file_tree(
            {
                "exclusions.yml": "_exclude: ['*.yml']",
                "common_jinja.yml": f"""
                    _templates_suffix: {SUFFIX_TMPL}
                    _envops:
                        block_start_string: "[%"
                        block_end_string: "%]"
                        comment_start_string: "[#"
                        comment_end_string: "#]"
                        variable_start_string: "[["
                        variable_end_string: "]]"
                        keep_trailing_newline: true
                    """,
                "common_questions.yml": """
                    your_age:
                        type: int
                    your_name:
                        type: yaml
                        help: your name from common questions
                    """,
                "copier.yml": """
                    ---
                    !include 'common_*.yml'
                    ---
                    !include exclusions.yml
                    ---
                    your_name:
                        type: str
                        help: your name from latest section
                    """,
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


def test_config_data_empty():
    template = Template("tests/demo_config_empty")
    assert template.config_data == {"secret_questions": set()}
    assert template.questions_data == {}


def test_multiple_config_file_error():
    template = Template("tests/demo_multi_config")
    with pytest.raises(MultipleConfigFilesError):
        template.config_data


# ConfigData
@pytest.mark.parametrize(
    "data",
    (
        {"pretend": "not_a_bool"},
        {"quiet": "not_a_bool"},
        {"force": "not_a_bool"},
        {"cleanup_on_error": "not_a_bool"},
        {"force": True, "skip_if_exists": True},
    ),
)
def test_flags_bad_data(data):
    with pytest.raises(ValidationError):
        copier.Worker(**data)


def test_flags_extra_fails():
    key = "i_am_not_a_member"
    conf_data = {"src_path": "..", "dst_path": ".", key: "and_i_do_not_belong_here"}
    with pytest.raises(TypeError):
        copier.Worker(**conf_data)


def test_missing_template(tmp_path):
    with pytest.raises(ValueError):
        copier.copy("./i_do_not_exist", tmp_path)


def is_subdict(small, big):
    return {**big, **small} == big


def test_worker_good_data(tmp_path):
    # This test is probably useless, as it tests the what and not the how
    conf = copier.Worker("./tests/demo_data", tmp_path)
    assert conf._render_context()["_folder_name"] == tmp_path.name
    assert conf.all_exclusions == ("exclude1", "exclude2")
    assert conf.template.skip_if_exists == ["skip_if_exists1", "skip_if_exists2"]
    assert conf.template.tasks == ["touch 1", "touch 2"]


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
def test_worker_config_precedence(tmp_path, test_input, expected_exclusions):
    conf = copier.Worker(dst_path=tmp_path, vcs_ref="HEAD", **test_input)
    assert expected_exclusions == conf.all_exclusions


def test_config_data_transclusion():
    config = copier.Worker("tests/demo_transclude/demo")
    assert config.all_exclusions == ("exclude1", "exclude2")
