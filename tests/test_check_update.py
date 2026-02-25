from __future__ import annotations

import pytest
from plumbum import local

from copier._cli import CopierApp

from .helpers import build_file_tree, git


@pytest.fixture(scope="module")
def template_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    src = tmp_path_factory.mktemp("src")

    # Create template v1.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            src / "copier.yml": (
                """\
                version: 1.0.0
                """
            ),
            src / "README.md.jinja": (
                """\
                # Version {{ version }}
                """
            ),
        }
    )
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "v1.0.0")
        git("tag", "v1.0.0")

    # Create template v2.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            src / "copier.yml": (
                """\
                version: 2.0.0
                """
            ),
            src / "README.md.jinja": (
                """\
                # Version {{ version }}
                """
            ),
        }
    )
    with local.cwd(src):
        git("add", ".")
        git("commit", "-m", "v2.0.0")
        git("tag", "v2.0.0")

    # Create template v3.0.0-alpha
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            src / "copier.yml": (
                """\
                version: 3.0.0-alpha
                """
            ),
            src / "README.md.jinja": (
                """\
                # Version {{ version }}
                """
            ),
        }
    )
    with local.cwd(src):
        git("add", ".")
        git("commit", "-m", "v3.0.0-alpha")
        git("tag", "v3.0.0-alpha")

    return str(src)


def test_without_updated_template_no_opts(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert "Project is up-to-date!" in captured.out


def test_without_updated_template_json_output_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--output-format",
            "json",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        '{"update_available": false, "current_version": "2.0.0", "latest_version": "2.0.0"}'
        in captured.out
    )


def test_without_updated_template_quiet_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--quiet",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_with_updated_template_no_opts(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        "New template version available.\nCurrent version is 1.0.0, latest version is 2.0.0."
        in captured.out
    )


def test_with_updated_template_json_output_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--output-format",
            "json",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        '{"update_available": true, "current_version": "1.0.0", "latest_version": "2.0.0"}'
        in captured.out
    )


def test_with_updated_template_quiet_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--quiet",
        ],
        exit=False,
    )
    assert run_result[1] == 2
    captured = capsys.readouterr()
    assert captured.out == ""


def test_with_prerelease_template_no_opts(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert "Project is up-to-date!" in captured.out


def test_with_prerelease_template_json_output_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--output-format",
            "json",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        '{"update_available": false, "current_version": "2.0.0", "latest_version": "2.0.0"}'
        in captured.out
    )


def test_with_prerelease_template_quiet_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--quiet",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_with_prerelease_template_prereleases_opt(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--prereleases",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        "New template version available.\nCurrent version is 2.0.0, latest version is 3.0.0a0."
        in captured.out
    )


def test_with_prerelease_template_prereleases_and_json_output_opts(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--output-format",
            "json",
            "--prereleases",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        '{"update_available": true, "current_version": "2.0.0", "latest_version": "3.0.0a0"}'
        in captured.out
    )


def test_with_prerelease_template_prereleases_and_quiet_opts(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    template_path: str,
) -> None:
    src = template_path
    dst = str(tmp_path_factory.mktemp("dst"))

    CopierApp.run(
        [
            "copier",
            "copy",
            src,
            dst,
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref=v2.0.0",
        ],
        exit=False,
    )

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--quiet",
            "--prereleases",
        ],
        exit=False,
    )
    assert run_result[1] == 2
    captured = capsys.readouterr()
    assert captured.out == ""
