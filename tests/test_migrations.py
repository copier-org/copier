import json
import platform
from glob import glob
from pathlib import Path

import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

from copier import copy
from copier.errors import UserMessageError

from .helpers import BRACKET_ENVOPS_JSON, build_file_tree


@pytest.fixture(scope="module")
def template_path(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("template")
    build_file_tree(
        {
            root
            / "[[ _copier_conf.answers_file ]].tmpl": """\
                # Changes here will be overwritten by Copier
                [[ _copier_answers|to_nice_yaml ]]
            """,
            root
            / "copier.yaml": """\
                _templates_suffix: .tmpl
                _envops:
                  autoescape: false
                  block_end_string: "%]"
                  block_start_string: "[%"
                  comment_end_string: "#]"
                  comment_start_string: "[#"
                  keep_trailing_newline: true
                  variable_end_string: "]]"
                  variable_start_string: "[["

                _exclude:
                  - tasks.py
                  - migrations.py
                  - .git

                _tasks:
                  - "python [[ _copier_conf.src_path / 'tasks.py' ]] 1"
                  - [python, "[[ _copier_conf.src_path / 'tasks.py' ]]", 2]

                _migrations:
                  # This migration is never executed because it's the 1st version copied, and
                  # migrations are only executed when updating
                  - version: v1.0.0
                    before:
                      - &mig
                        - python
                        - "[[ _copier_conf.src_path / 'migrations.py' ]]"
                        - "[[ _copier_conf.json() ]]"
                    after:
                      - *mig
                  - version: v2
                    before: [*mig]
                    after:
                      - *mig
                      - "rm delete-in-migration-v$VERSION_CURRENT.txt"
            """,
            root
            / "delete-in-migration-v2.txt": """\
                This file will be deleted after migrating to v2.
            """,
            root
            / "delete-in-tasks.txt": """\
                This file will be deleted in tasks.
            """,
            root
            / "migrations.py": """\
                #!/usr/bin/env python
                import json
                import os
                import sys

                NAME = "v{VERSION_FROM}-v{VERSION_CURRENT}-v{VERSION_TO}-{STAGE}.json"
                expanded_name = NAME.format(**os.environ)
                print(f"deleting {expanded_name}")

                with open(expanded_name, "w") as fd:
                    json.dump(sys.argv, fd)
            """,
            root
            / "tasks.py": """\
                #!/usr/bin/env python
                import os
                import os.path
                import sys
                from contextlib import suppress
                from subprocess import check_call

                with open("created-with-tasks.txt", "a", newline="\\n") as cwt:
                    cwt.write(" ".join([os.environ["STAGE"]] + sys.argv[1:]) + "\\n")
                    check_call(["git", "init"])
                    with suppress(FileNotFoundError):
                        os.unlink("delete-in-tasks.txt")
            """,
        }
    )
    return str(root)


# This fails on windows CI because, when the test tries to execute
# `migrations.py`, it doesn't understand that it should be interpreted
# by python.exe. Or maybe it fails because CI is using Git bash instead
# of WSL bash, which happened to work fine in real world tests.
# FIXME Some generous Windows power user please fix this test!
@pytest.mark.xfail(
    condition=platform.system() == "Windows",
    reason="Windows ignores shebang?",
    strict=True,
)
def test_migrations_and_tasks(tmp_path: Path, template_path: str):
    """Check migrations and tasks are run properly."""
    # Convert demo_migrations in a git repository with 2 versions
    git_src, dst = template_path, tmp_path / "tmp_path"
    with local.cwd(git_src):
        git("init")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1.0.0")
        git("commit", "--allow-empty", "-m2")
        git("tag", "v2.0")
    # Copy it in v1
    copy(src_path=str(git_src), dst_path=str(dst), vcs_ref="v1.0.0")
    # Check copy was OK
    assert (dst / "created-with-tasks.txt").read_text() == "task 1\ntask 2\n"
    assert not (dst / "delete-in-tasks.txt").exists()
    assert (dst / "delete-in-migration-v2.txt").is_file()
    assert not (dst / "migrations.py").exists()
    assert not (dst / "tasks.py").exists()
    assert not glob(str(dst / "*-before.txt"))
    assert not glob(str(dst / "*-after.txt"))
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers == {"_commit": "v1.0.0", "_src_path": str(git_src)}
    # Save changes in downstream repo
    with local.cwd(dst):
        git("add", ".")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("commit", "-m1")
    # Update it to v2
    copy(dst_path=str(dst), defaults=True, overwrite=True)
    # Check update was OK
    assert (dst / "created-with-tasks.txt").read_text() == "task 1\ntask 2\n" * 2
    assert not (dst / "delete-in-tasks.txt").exists()
    assert not (dst / "delete-in-migration-v2.txt").exists()
    assert not (dst / "migrations.py").exists()
    assert not (dst / "tasks.py").exists()
    assert (dst / "v1.0.0-v2-v2.0-before.json").is_file()
    assert (dst / "v1.0.0-v2-v2.0-after.json").is_file()
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers == {"_commit": "v2.0", "_src_path": str(git_src)}


def test_pre_migration_modifies_answers(tmp_path_factory):
    """Test support for answers modifications in pre-migrations."""
    template = tmp_path_factory.mktemp("template")
    subproject = tmp_path_factory.mktemp("subproject")
    # v1 of template asks for a favourite song and writes it to songs.json
    with local.cwd(template):
        build_file_tree(
            {
                "[[ _copier_conf.answers_file ]].jinja": "[[ _copier_answers|tojson ]]",
                "copier.yml": f"""\
                    _envops: {BRACKET_ENVOPS_JSON}
                    best_song: la vie en rose
                    """,
                "songs.json.jinja": "[ [[ best_song|tojson ]] ]",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1")
    # User copies v1 template into subproject
    with local.cwd(subproject):
        copy(src_path=str(template), defaults=True, overwrite=True)
        answers = json.loads(Path(".copier-answers.yml").read_text())
        assert answers["_commit"] == "v1"
        assert answers["best_song"] == "la vie en rose"
        assert json.loads(Path("songs.json").read_text()) == ["la vie en rose"]
        git("init")
        git("add", ".")
        git("commit", "-m1")
    with local.cwd(template):
        build_file_tree(
            {
                # v2 of template supports multiple songs, has a different default
                # and includes a data format migration script
                "copier.yml": f"""\
                    _envops: {BRACKET_ENVOPS_JSON}
                    best_song_list:
                      default: [paranoid android]
                    _migrations:
                      - version: v2
                        before:
                          - - python
                            - -c
                            - |
                                import sys, json, pathlib
                                answers_path = pathlib.Path(*sys.argv[1:])
                                answers = json.loads(answers_path.read_text())
                                answers["best_song_list"] = [answers.pop("best_song")]
                                answers_path.write_text(json.dumps(answers))
                            - "[[ _copier_conf.dst_path ]]"
                            - "[[ _copier_conf.answers_file ]]"
                    """,
                "songs.json.jinja": "[[ best_song_list|tojson ]]",
            }
        )
        git("add", ".")
        git("commit", "-m2")
        git("tag", "v2")
    # User updates subproject to v2 template
    with local.cwd(subproject):
        copy(defaults=True, overwrite=True)
        answers = json.loads(Path(".copier-answers.yml").read_text())
        assert answers["_commit"] == "v2"
        assert "best_song" not in answers
        assert answers["best_song_list"] == ["la vie en rose"]
        assert json.loads(Path("songs.json").read_text()) == ["la vie en rose"]


def test_prereleases(tmp_path: Path):
    """Test prereleases support for copying and updating."""
    src, dst = tmp_path / "src", tmp_path / "dst"
    src.mkdir()
    with local.cwd(src):
        # Build template in v1.0.0
        build_file_tree(
            {
                "version.txt": "v1.0.0",
                "[[ _copier_conf.answers_file ]].jinja": "[[_copier_answers|to_nice_yaml]]",
                "copier.yaml": f"""
                    _envops: {BRACKET_ENVOPS_JSON}
                    _migrations:
                      - version: v1.9
                        before:
                          - [python, -c, "import pathlib; pathlib.Path('v1.9').touch()"]
                      - version: v2.dev0
                        before:
                          - [python, -c, "import pathlib; pathlib.Path('v2.dev0').touch()"]
                      - version: v2.dev2
                        before:
                          - [python, -c, "import pathlib; pathlib.Path('v2.dev2').touch()"]
                      - version: v2.a1
                        before:
                          - [python, -c, "import pathlib; pathlib.Path('v2.a1').touch()"]
                      - version: v2.a2
                        before:
                          - [python, -c, "import pathlib; pathlib.Path('v2.a2').touch()"]
                """,
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-mv1")
        git("tag", "v1.0.0")
        # Evolve template to v2.0.0.dev1
        build_file_tree({"version.txt": "v2.0.0.dev1"})
        git("commit", "-amv2dev1")
        git("tag", "v2.0.0.dev1")
        # Evolve template to v2.0.0.alpha1
        build_file_tree({"version.txt": "v2.0.0.alpha1"})
        git("commit", "-amv2a1")
        git("tag", "v2.0.0.alpha1")
    # Copying with use_prereleases=False copies v1
    copy(src_path=str(src), dst_path=dst, defaults=True, overwrite=True)
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v1.0.0"
    assert (dst / "version.txt").read_text() == "v1.0.0"
    assert not (dst / "v1.9").exists()
    assert not (dst / "v2.dev0").exists()
    assert not (dst / "v2.dev2").exists()
    assert not (dst / "v2.a1").exists()
    assert not (dst / "v2.a2").exists()
    with local.cwd(dst):
        # Commit subproject
        git("init")
        git("add", ".")
        git("commit", "-mv1")
        # Update it without prereleases; nothing changes
        copy(defaults=True, overwrite=True)
        assert not git("status", "--porcelain")
    assert not (dst / "v1.9").exists()
    assert not (dst / "v2.dev0").exists()
    assert not (dst / "v2.dev2").exists()
    assert not (dst / "v2.a1").exists()
    assert not (dst / "v2.a2").exists()
    # Update it with prereleases
    copy(dst_path=dst, defaults=True, overwrite=True, use_prereleases=True)
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v2.0.0.alpha1"
    assert (dst / "version.txt").read_text() == "v2.0.0.alpha1"
    assert (dst / "v1.9").exists()
    assert (dst / "v2.dev0").exists()
    assert (dst / "v2.dev2").exists()
    assert (dst / "v2.a1").exists()
    assert not (dst / "v2.a2").exists()
    # It should fail if downgrading
    with pytest.raises(UserMessageError):
        copy(dst_path=dst, defaults=True, overwrite=True)
