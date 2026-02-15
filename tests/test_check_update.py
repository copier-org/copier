from __future__ import annotations

import pytest
from plumbum import local

from copier._cli import CopierApp

from .helpers import (
    build_file_tree,
    git,
)


@pytest.fixture(scope="module")
def src_and_dst_no_update(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    src_str, dst_str = map(str, (src, dst))

    # Create template v1.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            src / "copier.yml": """\
                version: 1.0.0
                """,
            src / "README.md.jinja": """\
                # Version {{ version }}
                """,
        }
    )
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "v1.0.0")
        git("tag", "v1.0.0")

    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            src_str,
            dst_str,
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    return src_str, dst_str


@pytest.fixture(scope="module")
def src_and_dst_update_available(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, str]:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    src_str, dst_str = map(str, (src, dst))

    # Create template v1.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            src / "copier.yml": """\
                version: 1.0.0
                """,
            src / "README.md.jinja": """\
                # Version {{ version }}
                """,
        }
    )
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "v1.0.0")
        git("tag", "v1.0.0")

    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            src_str,
            dst_str,
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    # Create template v2.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            src / "copier.yml": """\
                version: 2.0.0
                """,
            src / "README.md.jinja": """\
                # Version {{ version }}
                """,
        }
    )
    with local.cwd(src):
        git("add", ".")
        git("commit", "-m", "v2.0.0")
        git("tag", "v2.0.0")

    return src_str, dst_str


@pytest.fixture(scope="module")
def src_and_dst_prerelease_update_available(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, str]:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    src_str, dst_str = map(str, (src, dst))

    # Create template v1.0.0
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            src / "copier.yml": """\
                version: 1.0.0
                """,
            src / "README.md.jinja": """\
                # Version {{ version }}
                """,
        }
    )
    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-m", "v1.0.0")
        git("tag", "v1.0.0")

    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            src_str,
            dst_str,
            "--defaults",
            "--overwrite",
            "--vcs-ref=v1.0.0",
        ],
        exit=False,
    )

    # Create template v2.0.0-alpha
    build_file_tree(
        {
            src / "{{ _copier_conf.answers_file }}.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """,
            src / "copier.yml": """\
                version: 2.0.0-alpha
                """,
            src / "README.md.jinja": """\
                # Version {{ version }}
                """,
        }
    )
    with local.cwd(src):
        git("add", ".")
        git("commit", "-m", "v2.0.0-alpha")
        git("tag", "v2.0.0-alpha")

    return src_str, dst_str


def test_without_updated_template_no_opts(
    src_and_dst_no_update: tuple[str, str],
) -> None:
    src, dst = src_and_dst_no_update

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 0


def test_without_updated_template_json_output_opt(
    capsys: pytest.CaptureFixture[str], src_and_dst_no_update: tuple[str, str]
) -> None:
    src, dst = src_and_dst_no_update

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
        '{"update_available": false, "current_version": "1.0.0", "latest_version": "1.0.0"}'
        in captured.out
    )


def test_with_updated_template_no_opts(
    src_and_dst_update_available: tuple[str, str],
) -> None:
    src, dst = src_and_dst_update_available

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 5


def test_with_updated_template_json_output_opt(
    capsys: pytest.CaptureFixture[str], src_and_dst_update_available: tuple[str, str]
) -> None:
    src, dst = src_and_dst_update_available

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
    assert run_result[1] == 5
    captured = capsys.readouterr()
    assert (
        '{"update_available": true, "current_version": "1.0.0", "latest_version": "2.0.0"}'
        in captured.out
    )


def test_with_prerelease_template_no_opts(
    src_and_dst_prerelease_update_available: tuple[str, str],
) -> None:
    src, dst = src_and_dst_prerelease_update_available

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
        ],
        exit=False,
    )
    assert run_result[1] == 0


def test_with_prerelease_template_json_output_opt(
    capsys: pytest.CaptureFixture[str],
    src_and_dst_prerelease_update_available: tuple[str, str],
) -> None:
    src, dst = src_and_dst_prerelease_update_available

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
        '{"update_available": false, "current_version": "1.0.0", "latest_version": "1.0.0"}'
        in captured.out
    )


def test_with_prerelease_template_prereleases_opt(
    src_and_dst_prerelease_update_available: tuple[str, str],
) -> None:
    src, dst = src_and_dst_prerelease_update_available

    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            dst,
            "--prereleases",
        ],
        exit=False,
    )
    assert run_result[1] == 5


def test_with_prerelease_template_prereleases_and_json_output_opts(
    capsys: pytest.CaptureFixture[str],
    src_and_dst_prerelease_update_available: tuple[str, str],
) -> None:
    src, dst = src_and_dst_prerelease_update_available

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
    assert run_result[1] == 5
    captured = capsys.readouterr()
    assert (
        '{"update_available": true, "current_version": "1.0.0", "latest_version": "2.0.0a0"}'
        in captured.out
    )
