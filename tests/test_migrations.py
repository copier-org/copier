import json
import platform
from glob import glob
from pathlib import Path
from shutil import copytree

import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

from copier import copy

from .helpers import PROJECT_TEMPLATE, build_file_tree

SRC = Path(f"{PROJECT_TEMPLATE}_migrations").absolute()


def test_migrations_and_tasks(tmp_path: Path):
    """Check migrations and tasks are run properly."""
    if platform.system() == "Windows":
        # This fails on windows CI because, when the test tries to execute
        # `migrations.py`, it doesn't understand that it should be interpreted
        # by python.exe. Or maybe it fails because CI is using Git bash instead
        # of WSL bash, which happened to work fine in real world tests.
        # FIXME Some generous Windows power user please fix this test!
        pytest.skip("Skipping test that will fail on Windows")
    # Convert demo_migrations in a git repository with 2 versions
    git_src, dst = tmp_path / "src", tmp_path / "tmp_path"
    copytree(SRC, git_src)
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
    copy(dst_path=str(dst), force=True)
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
                "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|tojson ]]",
                "copier.yml": """\
                    best_song: la vie en rose
                    """,
                "songs.json.tmpl": "[ [[ best_song|tojson ]] ]",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1")
    # User copies v1 template into subproject
    with local.cwd(subproject):
        copy(src_path=str(template), force=True)
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
                "copier.yml": """\
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
                "songs.json.tmpl": "[[ best_song_list|tojson ]]",
            }
        )
        git("add", ".")
        git("commit", "-m2")
        git("tag", "v2")
    # User updates subproject to v2 template
    with local.cwd(subproject):
        copy(force=True)
        answers = json.loads(Path(".copier-answers.yml").read_text())
        assert answers["_commit"] == "v2"
        assert "best_song" not in answers
        assert answers["best_song_list"] == ["la vie en rose"]
        assert json.loads(Path("songs.json").read_text()) == ["la vie en rose"]
