from __future__ import annotations

from textwrap import dedent

import pytest
from plumbum import local

from copier._cli import CopierApp
from copier._user_data import load_answersfile_data

from .helpers import (
    build_file_tree,
    git,
)


@pytest.mark.impure
def test_with_updated_template_no_opts(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Prepare repo bundle
    repo = src / "repo"
    bundle = src / "demo_check_update_repo.bundle"
    build_file_tree(
        {
            (repo / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}, and my project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Guybrush wants to be a pirate")
        git("tag", "v0.0.1")
    build_file_tree(
        {
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to rule
                author_name: Elaine
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}.

                My project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Elaine wants to rule")
        git("tag", "v0.0.2")
        git("bundle", "create", bundle, "--all")
    # Generate repo bundle
    target = dst / "target"
    readme = target / "README.txt"
    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            str(bundle),
            str(target),
            "--defaults",
            "--overwrite",
            "--vcs-ref=v0.0.1",
        ],
        exit=False,
    )
    # Check it's copied OK
    assert load_answersfile_data(target) == {
        "_commit": "v0.0.1",
        "_src_path": str(bundle),
        "author_name": "Guybrush",
        "project_name": "to become a pirate",
    }
    assert readme.read_text() == dedent(
        """
        Let me introduce myself.

        My name is Guybrush, and my project is to become a pirate.

        Thanks for your attention.
        """
    )
    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            str(target),
        ],
        exit=False,
    )
    print("hey there")
    assert run_result[1] == 5


@pytest.mark.impure
def test_with_updated_template_json_output(
    tmp_path_factory: pytest.TempPathFactory, capsys
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Prepare repo bundle
    repo = src / "repo"
    bundle = src / "demo_check_update_repo.bundle"
    build_file_tree(
        {
            (repo / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}, and my project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Guybrush wants to be a pirate")
        git("tag", "v0.0.1")
    build_file_tree(
        {
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to rule
                author_name: Elaine
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}.

                My project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Elaine wants to rule")
        git("tag", "v0.0.2")
        git("bundle", "create", bundle, "--all")
    # Generate repo bundle
    target = dst / "target"
    readme = target / "README.txt"
    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            str(bundle),
            str(target),
            "--defaults",
            "--overwrite",
            "--vcs-ref=v0.0.1",
        ],
        exit=False,
    )
    # Check it's copied OK
    assert load_answersfile_data(target) == {
        "_commit": "v0.0.1",
        "_src_path": str(bundle),
        "author_name": "Guybrush",
        "project_name": "to become a pirate",
    }
    assert readme.read_text() == dedent(
        """
        Let me introduce myself.

        My name is Guybrush, and my project is to become a pirate.

        Thanks for your attention.
        """
    )
    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            str(target),
            "--check-update-output-as-json",
        ],
        exit=False,
    )
    assert run_result[1] == 5
    captured = capsys.readouterr()
    assert (
        '{"update_available": true, "current_version": "0.0.1", "latest_version": "0.0.2"}'
        in captured.out
    )


@pytest.mark.impure
def test_without_updated_template_no_opts(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Prepare repo bundle
    repo = src / "repo"
    bundle = src / "demo_check_update_repo.bundle"
    build_file_tree(
        {
            (repo / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}, and my project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Guybrush wants to be a pirate")
        git("tag", "v0.0.1")
        git("bundle", "create", bundle, "--all")
    # Generate repo bundle
    target = dst / "target"
    readme = target / "README.txt"
    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            str(bundle),
            str(target),
            "--defaults",
            "--overwrite",
            "--vcs-ref=v0.0.1",
        ],
        exit=False,
    )
    # Check it's copied OK
    assert load_answersfile_data(target) == {
        "_commit": "v0.0.1",
        "_src_path": str(bundle),
        "author_name": "Guybrush",
        "project_name": "to become a pirate",
    }
    assert readme.read_text() == dedent(
        """
        Let me introduce myself.

        My name is Guybrush, and my project is to become a pirate.

        Thanks for your attention.
        """
    )
    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            str(target),
        ],
        exit=False,
    )
    assert run_result[1] == 0


@pytest.mark.impure
def test_without_updated_template_json_output(
    tmp_path_factory: pytest.TempPathFactory, capsys
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Prepare repo bundle
    repo = src / "repo"
    bundle = src / "demo_check_update_repo.bundle"
    build_file_tree(
        {
            (repo / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (repo / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
                """
            ),
            (repo / "README.txt.jinja"): (
                """
                Let me introduce myself.

                My name is {{author_name}}, and my project is {{project_name}}.

                Thanks for your attention.
                """
            ),
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Guybrush wants to be a pirate")
        git("tag", "v0.0.1")
        git("bundle", "create", bundle, "--all")
    # Generate repo bundle
    target = dst / "target"
    readme = target / "README.txt"
    # Run copier 1st time, with specific tag
    CopierApp.run(
        [
            "copier",
            "copy",
            str(bundle),
            str(target),
            "--defaults",
            "--overwrite",
            "--vcs-ref=v0.0.1",
        ],
        exit=False,
    )
    # Check it's copied OK
    assert load_answersfile_data(target) == {
        "_commit": "v0.0.1",
        "_src_path": str(bundle),
        "author_name": "Guybrush",
        "project_name": "to become a pirate",
    }
    assert readme.read_text() == dedent(
        """
        Let me introduce myself.

        My name is Guybrush, and my project is to become a pirate.

        Thanks for your attention.
        """
    )
    run_result = CopierApp.run(
        [
            "copier",
            "check-update",
            str(target),
            "--check-update-output-as-json",
        ],
        exit=False,
    )
    assert run_result[1] == 0
    captured = capsys.readouterr()
    assert (
        '{"update_available": false, "current_version": "0.0.1", "latest_version": "0.0.1"}'
        in captured.out
    )
