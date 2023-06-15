import re
from pathlib import Path

import pexpect
import pytest

from copier.errors import InvalidTypeError
from copier.main import run_copy, run_recopy

from .helpers import COPIER_PATH, Spawn, build_file_tree, expect_prompt, render


def test_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=False)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_pretend(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=False, pretend=True)
    _, err = capsys.readouterr()
    assert re.search(r"create[^\s]*  config\.py", err)
    assert re.search(r"create[^\s]*  pyproject\.toml", err)
    assert re.search(r"create[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_force(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, defaults=True, overwrite=True)
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"overwrite[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_skip(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path)
    capsys.readouterr()
    render(tmp_path, quiet=False, skip_if_exists=["config.py"])
    _, err = capsys.readouterr()
    assert re.search(r"conflict[^\s]*  config\.py", err)
    assert re.search(r"skip[^\s]*  config\.py", err)
    assert re.search(r"identical[^\s]*  pyproject\.toml", err)
    assert re.search(r"identical[^\s]*  doc[/\\]images[/\\]nslogo\.gif", err)


def test_output_quiet(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    render(tmp_path, quiet=True)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_question_with_invalid_type(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            src
            / "copier.yaml": """
                bad:
                    type: invalid
                    default: 1
                """
        }
    )
    with pytest.raises(
        InvalidTypeError, match='Unsupported type "invalid" in question "bad"'
    ):
        run_copy(str(src), dst, defaults=True, overwrite=True)


def test_answer_with_invalid_type(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            src
            / "copier.yaml": """
                bad:
                    type: int
                    default: null
                """
        }
    )
    with pytest.raises(
        InvalidTypeError,
        match='Invalid answer "None" of type "<class \'NoneType\'>" to question "bad" of type "int"',
    ):
        run_copy(str(src), dst, defaults=True, overwrite=True)


@pytest.mark.parametrize("interactive", [False, True])
def test_message_copy_with_inline_text(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    spawn: Spawn,
    interactive: bool,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                project_name:
                    type: str

                _message_before_copy: Thank you for using our template on {{ _copier_conf.os }}
                _message_after_copy: Project {{ project_name }} successfully created
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

    pattern = (
        r"^"
        r"Thank you for using our template on (linux|macos|windows)"
        r".+"
        r"Project {project_name} successfully created"
        r"\s*"
        r"$"
    )

    # copy
    if interactive:
        tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("myproj")
        tui.expect_exact(pexpect.EOF)
    else:
        run_copy(str(src), dst, data={"project_name": "myproj"})

    _, err = capsys.readouterr()
    assert re.search(pattern.format(project_name="myproj"), err, flags=re.S)

    # recopy
    if interactive:
        tui = spawn(COPIER_PATH + ("recopy", str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("_new")
        tui.expect_exact(pexpect.EOF)
    else:
        run_recopy(dst, data={"project_name": "myproj_new"})

    _, err = capsys.readouterr()
    assert re.search(pattern.format(project_name="myproj_new"), err, flags=re.S)


@pytest.mark.parametrize("interactive", [False, True])
def test_message_copy_with_included_text(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    spawn: Spawn,
    interactive: bool,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                project_name:
                    type: str

                _exclude: ["*.md"]
                _message_before_copy: "{% include 'message_before_copy.md.jinja' %}"
                _message_after_copy: "{% include 'message_after_copy.md.jinja' %}"
                """
            ),
            (src / "message_before_copy.md.jinja"): (
                """\
                Thank you for using our template on {{ _copier_conf.os }}
                """
            ),
            (src / "message_after_copy.md.jinja"): (
                """\
                Project {{ project_name }} successfully created
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

    pattern = (
        r"^"
        r"Thank you for using our template on (linux|macos|windows)"
        r".+"
        r"Project {project_name} successfully created"
        r"\s*"
        r"$"
    )

    # copy
    if interactive:
        tui = spawn(COPIER_PATH + ("copy", str(src), str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("myproj")
        tui.expect_exact(pexpect.EOF)
    else:
        run_copy(str(src), dst, data={"project_name": "myproj"})

    _, err = capsys.readouterr()
    assert re.search(pattern.format(project_name="myproj"), err, flags=re.S)

    # recopy
    if interactive:
        tui = spawn(COPIER_PATH + ("recopy", str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("_new")
        tui.expect_exact(pexpect.EOF)
    else:
        run_recopy(dst, data={"project_name": "myproj_new"})

    _, err = capsys.readouterr()
    assert re.search(pattern.format(project_name="myproj_new"), err, flags=re.S)


@pytest.mark.parametrize("interactive", [False, True])
def test_message_copy_quiet(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    spawn: Spawn,
    interactive: bool,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                project_name:
                    type: str

                _message_before_copy: Thank you for using our template on {{ _copier_conf.os }}
                _message_after_copy: Project {{ project_name }} successfully created
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

    # copy
    if interactive:
        tui = spawn(COPIER_PATH + ("copy", "--quiet", str(src), str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("myproj")
        tui.expect_exact(pexpect.EOF)
    else:
        run_copy(str(src), dst, data={"project_name": "myproj"}, quiet=True)

    _, err = capsys.readouterr()
    assert "Thank you for using our template" not in err
    assert "Project myproj successfully created" not in err

    # recopy
    if interactive:
        tui = spawn(COPIER_PATH + ("recopy", "--quiet", str(dst)), timeout=10)
        expect_prompt(tui, "project_name", "str")
        tui.sendline("_new")
        tui.expect_exact(pexpect.EOF)
    else:
        run_recopy(dst, data={"project_name": "myproj_new"}, quiet=True)

    _, err = capsys.readouterr()
    assert "Thank you for using our template" not in err
    assert "Project myproj_new successfully created" not in err
