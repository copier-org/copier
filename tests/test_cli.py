from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from inline_snapshot import snapshot
from plumbum import local

from copier._cli import CopierApp
from copier._user_data import load_answersfile_data

from .helpers import COPIER_CMD, build_file_tree, git


@pytest.fixture(scope="module")
def template_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            (root / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (root / "a.txt"): "EXAMPLE_CONTENT",
        }
    )
    return str(root)


@pytest.fixture(scope="module")
def template_path_with_dot_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Callable[[str], str], str, None]:
    def _template_path_with_dot_config(config_folder: str) -> str:
        root = tmp_path_factory.mktemp("template")
        build_file_tree(
            {
                root / config_folder / "{{ _copier_conf.answers_file }}.jinja": """\
                    # Changes here will be overwritten by Copier
                    {{ _copier_answers|to_nice_yaml }}
                    """,
                root / "a.txt": "EXAMPLE_CONTENT",
            }
        )
        return str(root)

    yield _template_path_with_dot_config


def test_good_cli_run(template_path: str, tmp_path: Path) -> None:
    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            "--quiet",
            "-a",
            "altered-answers.yml",
            template_path,
            str(tmp_path),
        ],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "EXAMPLE_CONTENT"
    answers = load_answersfile_data(tmp_path, "altered-answers.yml")
    assert answers["_src_path"] == template_path


@pytest.mark.parametrize(
    "type_, answer, expected",
    [
        ("str", "string", "string"),
        ("str", "1", "1"),
        ("str", "1.2", "1.2"),
        ("str", "true", "true"),
        ("str", "null", "null"),
        ("str", '["string", 1, 1.2, true, null]', '["string", 1, 1.2, true, null]'),
        ("int", "1", 1),
        ("float", "1.2", 1.2),
        ("bool", "true", True),
        ("bool", "false", False),
        ("yaml", '"string"', "string"),
        ("yaml", "1", 1),
        ("yaml", "1.2", 1.2),
        ("yaml", "true", True),
        ("yaml", "null", None),
        ("yaml", '["string", 1, 1.2, true, null]', ["string", 1, 1.2, True, None]),
        ("json", '"string"', "string"),
        ("json", "1", 1),
        ("json", "1.2", 1.2),
        ("json", "true", True),
        ("json", "null", None),
        ("json", '["string", 1, 1.2, true, null]', ["string", 1, 1.2, True, None]),
    ],
)
def test_cli_data_parsed_by_question_type(
    tmp_path_factory: pytest.TempPathFactory, type_, answer, expected
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                question:
                    type: {type_}
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
    run_result = CopierApp.run(
        ["copier", "copy", f"--data=question={answer}", str(src), str(dst), "--quiet"],
        exit=False,
    )
    assert run_result[1] == 0
    answers = load_answersfile_data(dst)
    assert answers["_src_path"] == str(src)
    assert answers["question"] == expected


def test_data_file_parsed_by_question_type(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst, local = map(tmp_path_factory.mktemp, ("src", "dst", "local"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                question:
                    type: str
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (local / "data.yml"): yaml.dump({"question": "answer"}),
        }
    )

    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            f"--data-file={local / 'data.yml'}",
            str(src),
            str(dst),
            "--quiet",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    answers = load_answersfile_data(dst)
    assert answers["_src_path"] == str(src)
    assert answers["question"] == "answer"


def test_data_cli_takes_precedence_over_data_file(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst, local = map(tmp_path_factory.mktemp, ("src", "dst", "local"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                question:
                    type: str
                another_question:
                    type: str
                yet_another_question:
                    type: str
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (local / "data.yml"): yaml.dump(
                {
                    "question": "does not matter",
                    "another_question": "another answer!",
                    "yet_another_question": "sure, one more for you!",
                }
            ),
        }
    )

    answer_override = "fourscore and seven years ago"
    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            f"--data-file={local / 'data.yml'}",
            f"--data=question={answer_override}",
            str(src),
            str(dst),
            "--quiet",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    actual_answers = load_answersfile_data(dst)
    expected_answers = {
        "_src_path": str(src),
        "question": answer_override,
        "another_question": "another answer!",
        "yet_another_question": "sure, one more for you!",
    }
    assert actual_answers == expected_answers


@pytest.mark.parametrize(
    "data_file_encoding",
    ["utf-8", "utf-8-sig", "utf-16-le", "utf-16-be"],
)
def test_read_utf_data_file(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    data_file_encoding: str,
) -> None:
    src, dst, local = map(tmp_path_factory.mktemp, ("src", "dst", "local"))

    def encode_data(data: dict[str, str]) -> bytes:
        dump = yaml.dump(data, allow_unicode=True)
        if data_file_encoding.startswith("utf-16"):
            dump = "\ufeff" + dump
        return dump.encode(data_file_encoding)

    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                text1:
                    type: str
                text2:
                    type: str
                """
            ),
            (src / "{{ _copier_conf.answers_file }}.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (local / "data.yml"): encode_data(
                {
                    "text1": "\u3053\u3093\u306b\u3061\u306f",  # japanese hiragana
                    "text2": "\U0001f60e",  # smiling face with sunglasses
                }
            ),
        }
    )

    with monkeypatch.context() as m:
        # Override the factor that determine the default encoding when opening files.
        # data.yml should be read correctly regardless of this value.
        m.setattr("io.text_encoding", lambda *_args: "cp932")
        run_result = CopierApp.run(
            [
                "copier",
                "copy",
                f"--data-file={local / 'data.yml'}",
                str(src),
                str(dst),
            ],
            exit=False,
        )

    assert run_result[1] == 0
    expected_answers = {
        "_src_path": str(src),
        "text1": "\u3053\u3093\u306b\u3061\u306f",
        "text2": "\U0001f60e",
    }
    answers = load_answersfile_data(dst)
    assert answers == expected_answers


@pytest.mark.parametrize(
    "config_folder",
    map(
        Path,
        ["", ".config/", ".config/subconfig/", ".config/subconfig/deep_nested_config/"],
    ),
)
def test_good_cli_run_dot_config(
    tmp_path: Path,
    template_path_with_dot_config: Callable[[str], str],
    config_folder: Path,
) -> None:
    """Function to test different locations of the answersfile.

    Added based on the discussion: https://github.com/copier-org/copier/discussions/859
    """

    src = template_path_with_dot_config(str(config_folder))

    with local.cwd(src):
        git_commands()

    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            "--quiet",
            "-a",
            str(config_folder / "altered-answers.yml"),
            src,
            str(tmp_path),
        ],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "EXAMPLE_CONTENT"
    answers = load_answersfile_data(tmp_path / config_folder, "altered-answers.yml")
    assert answers["_src_path"] == src

    with local.cwd(str(tmp_path)):
        git_commands()

    run_update = CopierApp.run(
        [
            "copier",
            "update",
            str(tmp_path),
            "--answers-file",
            str(config_folder / "altered-answers.yml"),
            "--quiet",
        ],
        exit=False,
    )
    assert run_update[1] == 0
    assert answers["_src_path"] == src


def git_commands() -> None:
    git("init")
    git("add", "-A")
    git("commit", "-m", "init")


def test_help() -> None:
    _help = COPIER_CMD("--help-all")
    assert "copier copy [SWITCHES] template_src destination_path" in _help
    assert "copier update [SWITCHES] [destination_path=.]" in _help


def test_copy_help(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("plumbum.cli.application.get_terminal_size", return_value=(80, 1)):
        _, status = CopierApp.run(["copier", "copy", "--help"], exit=False)
    assert status == 0
    header, body = capsys.readouterr().out.split("\n", 1)
    assert header.startswith("copier copy")
    assert body == snapshot("""\

Copy from a template source to a destination.

Usage:
    copier copy [SWITCHES] template_src destination_path

Meta-switches:
    -h, --help                      Prints this help message and quits
    --help-all                      Prints help messages of all sub-commands and
                                    quits
    -v, --version                   Prints the program's version and quits

Switches:
    -C, --no-cleanup                On error, do not delete destination if it
                                    was created by Copier.
    -T, --skip-tasks                Skip template tasks execution
    --UNSAFE, --trust               Allow templates with unsafe features (Jinja
                                    extensions, migrations, tasks)
    -a, --answers-file VALUE:str    Update using this path (relative to
                                    `destination_path`) to find the answers file
    -d, --data VARIABLE=VALUE:str   Make VARIABLE available as VALUE when
                                    rendering the template; may be given
                                    multiple times
    --data-file PATH:ExistingFile   Load data from a YAML file
    -f, --force                     Same as `--defaults --overwrite`.
    -g, --prereleases               Use prereleases to compare template VCS
                                    tags.
    -l, --defaults                  Use default answers to questions, which
                                    might be null if not specified.
    -n, --pretend                   Run but do not make any changes
    -q, --quiet                     Suppress status output
    -r, --vcs-ref VALUE:str         Git reference to checkout in `template_src`.
                                    If you do not specify it, it will try to
                                    checkout the latest git tag, as sorted using
                                    the PEP 440 algorithm. If you want to
                                    checkout always the latest version, use
                                    `--vcs-ref=HEAD`. Use the special value
                                    `:current:` to refer to the current
                                    reference of the template if it already
                                    exists.
    -s, --skip VALUE:str            Skip specified files if they exist already;
                                    may be given multiple times
    -w, --overwrite                 Overwrite files that already exist, without
                                    asking.
    -x, --exclude VALUE:str         A name or shell-style pattern matching files
                                    or folders that must not be copied; may be
                                    given multiple times

""")


def test_update_help(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("plumbum.cli.application.get_terminal_size", return_value=(80, 1)):
        _, status = CopierApp.run(["copier", "update", "--help"], exit=False)
    assert status == 0
    header, body = capsys.readouterr().out.split("\n", 1)
    assert header.startswith("copier update")
    assert body == snapshot("""\

Update a subproject from its original template

The copy must have a valid answers file which contains info from the last Copier
execution, including the source template (it must be a key called `_src_path`).

If that file contains also `_commit`, and `destination_path` is a git
repository, this command will do its best to respect the diff that you have
generated since the last `copier` execution. To avoid that, use `copier recopy`
instead.

Usage:
    copier update [SWITCHES] [destination_path=.]

Meta-switches:
    -h, --help                      Prints this help message and quits
    --help-all                      Prints help messages of all sub-commands and
                                    quits
    -v, --version                   Prints the program's version and quits

Switches:
    -A, --skip-answered             Skip questions that have already been
                                    answered
    -T, --skip-tasks                Skip template tasks execution
    --UNSAFE, --trust               Allow templates with unsafe features (Jinja
                                    extensions, migrations, tasks)
    -a, --answers-file VALUE:str    Update using this path (relative to
                                    `destination_path`) to find the answers file
    -c, --context-lines VALUE:int   Lines of context to use for detecting
                                    conflicts. Increase for accuracy, decrease
                                    for resilience.; the default is 3
    -d, --data VARIABLE=VALUE:str   Make VARIABLE available as VALUE when
                                    rendering the template; may be given
                                    multiple times
    --data-file PATH:ExistingFile   Load data from a YAML file
    -g, --prereleases               Use prereleases to compare template VCS
                                    tags.
    -l, -f, --defaults              Use default answers to questions, which
                                    might be null if not specified.
    -n, --pretend                   Run but do not make any changes
    -o, --conflict VALUE:{rej, inline} Behavior on conflict: Create .rej files, or
                                    add inline conflict markers.; the default is
                                    inline
    -q, --quiet                     Suppress status output
    -r, --vcs-ref VALUE:str         Git reference to checkout in `template_src`.
                                    If you do not specify it, it will try to
                                    checkout the latest git tag, as sorted using
                                    the PEP 440 algorithm. If you want to
                                    checkout always the latest version, use
                                    `--vcs-ref=HEAD`. Use the special value
                                    `:current:` to refer to the current
                                    reference of the template if it already
                                    exists.
    -s, --skip VALUE:str            Skip specified files if they exist already;
                                    may be given multiple times
    -x, --exclude VALUE:str         A name or shell-style pattern matching files
                                    or folders that must not be copied; may be
                                    given multiple times

""")


def test_check_update_help(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("plumbum.cli.application.get_terminal_size", return_value=(80, 1)):
        _, status = CopierApp.run(["copier", "check-update", "--help"], exit=False)
    assert status == 0
    header, body = capsys.readouterr().out.split("\n", 1)
    assert header.startswith("copier check-update")
    assert body == snapshot("""\

Check if a copy is using the latest version of its original template

The copy must have a valid answers file which contains info from the last Copier
execution, including the source template (it must be a key called `_src_path`).

If that file contains also `_commit` and `destination_path` is a git repository,
this command will do its best to determine whether a newer version is available,
applying PEP 440 to the template's history.

Usage:
    copier check-update [SWITCHES] [destination_path=.]

Meta-switches:
    -h, --help                      Prints this help message and quits
    --help-all                      Prints help messages of all sub-commands and
                                    quits
    -v, --version                   Prints the program's version and quits

Switches:
    -a, --answers-file VALUE:str    Check for updates using this path (relative
                                    to `destination_path`) to find the answers
                                    file
    -g, --prereleases               Use prereleases to compare template VCS
                                    tags.
    --output-format VALUE:{plain, json} Output format, either 'plain' (the default)
                                    or 'json'.; the default is plain
    -q, --quiet                     Suppress status output, exit with status 2
                                    when a new template version is available

""")


def test_inspect_help(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("plumbum.cli.application.get_terminal_size", return_value=(80, 1)):
        _, status = CopierApp.run(["copier", "inspect", "--help"], exit=False)
    assert status == 0
    header, body = capsys.readouterr().out.split("\n", 1)
    assert header.startswith("copier inspect")
    assert body == snapshot("""\

Inspect a template's questions and metadata

Usage:
    copier inspect [SWITCHES] template_src

Meta-switches:
    -h, --help                      Prints this help message and quits
    --help-all                      Prints help messages of all sub-commands and
                                    quits
    -v, --version                   Prints the program's version and quits

Switches:
    -g, --prereleases               Use prereleases to compare template VCS
                                    tags.
    --output-format VALUE:{json, plain, yaml} Output format: 'plain' (default),
                                    'json', or 'yaml'.; the default is plain
    -q, --quiet                     Suppress status output
    -r, --vcs-ref VALUE:str         Git reference to checkout in `template_src`.

""")


def test_python_run() -> None:
    cmd = [sys.executable, "-m", "copier", "--help-all"]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_skip_filenotexists(template_path: str, tmp_path: Path) -> None:
    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            "--quiet",
            "-a",
            "altered-answers.yml",
            "--overwrite",
            "--skip=a.txt",
            template_path,
            str(tmp_path),
        ],
        exit=False,
    )
    a_txt = tmp_path / "a.txt"
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "EXAMPLE_CONTENT"
    answers = load_answersfile_data(tmp_path, "altered-answers.yml")
    assert answers["_src_path"] == str(template_path)


def test_skip_fileexists(template_path: str, tmp_path: Path) -> None:
    a_txt = tmp_path / "a.txt"
    a_txt.write_text("PREVIOUS_CONTENT")
    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            "--quiet",
            "-a",
            "altered-answers.yml",
            "--overwrite",
            "--skip=a.txt",
            template_path,
            str(tmp_path),
        ],
        exit=False,
    )
    assert run_result[1] == 0
    assert a_txt.exists()
    assert a_txt.is_file()
    assert a_txt.read_text() == "PREVIOUS_CONTENT"
    answers = load_answersfile_data(tmp_path, "altered-answers.yml")
    assert answers["_src_path"] == str(template_path)


def test_data_with_multiselect_choice_question(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yml"): (
                """\
                q:
                    type: int
                    choices: [1, 2, 3]
                    multiselect: true
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

    run_result = CopierApp.run(
        [
            "copier",
            "copy",
            "--data=q=[1, 3]",
            str(src),
            str(dst),
        ],
        exit=False,
    )
    assert run_result[1] == 0
    assert load_answersfile_data(dst) == {"_src_path": str(src), "q": [1, 3]}
