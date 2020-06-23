from glob import glob
from pathlib import Path
from shutil import copytree

import py
import yaml
from plumbum import local
from plumbum.cmd import git

from copier import copy

from .helpers import PROJECT_TEMPLATE, build_file_tree

SRC = Path(f"{PROJECT_TEMPLATE}_migrations").absolute()


def test_migrations_and_tasks(tmpdir: py.path.local):
    """Check migrations and tasks are run properly."""
    # Convert demo_migrations in a git repository with 2 versions
    git_src, tmp_path = tmpdir / "src", tmpdir / "tmp_path"
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
    copy(src_path=str(git_src), dst_path=str(tmp_path), vcs_ref="v1.0.0")
    # Check copy was OK
    assert (tmp_path / "created-with-tasks.txt").read() == "task 1\ntask 2\n"
    assert not (tmp_path / "delete-in-tasks.txt").exists()
    assert (tmp_path / "delete-in-migration-v2.txt").isfile()
    assert not (tmp_path / "migrations.py").exists()
    assert not (tmp_path / "tasks.sh").exists()
    assert not glob(str(tmp_path / "*-before.txt"))
    assert not glob(str(tmp_path / "*-after.txt"))
    answers = yaml.safe_load((tmp_path / ".copier-answers.yml").read())
    assert answers == {"_commit": "v1.0.0", "_src_path": str(git_src)}
    # Save changes in downstream repo
    with local.cwd(tmp_path):
        git("add", ".")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("commit", "-m1")
    # Update it to v2
    copy(dst_path=str(tmp_path), force=True)
    # Check update was OK
    assert (tmp_path / "created-with-tasks.txt").read() == "task 1\ntask 2\n" * 2
    assert not (tmp_path / "delete-in-tasks.txt").exists()
    assert not (tmp_path / "delete-in-migration-v2.txt").exists()
    assert not (tmp_path / "migrations.py").exists()
    assert not (tmp_path / "tasks.sh").exists()
    assert (tmp_path / "v1.0.0-v2-v2.0-before.json").isfile()
    assert (tmp_path / "v1.0.0-v2-v2.0-after.json").isfile()
    answers = yaml.safe_load((tmp_path / ".copier-answers.yml").read())
    assert answers == {"_commit": "v2.0", "_src_path": str(git_src)}


def test_pre_migration_modifies_answers(tmp_path_factory):
    """Test support for answers modifications in pre-migrations."""
    template = tmp_path_factory.mktemp("template")
    subproject = tmp_path_factory.mktemp("subproject")
    # v1 of template asks for a favourite song and writes it to songs.yaml
    with local.cwd(template):
        build_file_tree(
            {
                "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
                "copier.yml": """\
                    best_song: la vie en rose
                    """,
                "songs.yaml.tmpl": "- [[ best_song ]]",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1")
    # User copies v1 template into subproject
    with local.cwd(subproject):
        copy(src_path=str(template), force=True)
        answers = yaml.safe_load(Path(".copier-answers.yml").read_text())
        assert answers["_commit"] == "v1"
        assert answers["best_song"] == "la vie en rose"
        assert yaml.safe_load(Path("songs.yaml").read_text()) == ["la vie en rose"]
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
                          - - python3
                            - -c
                            - |
                                import sys, yaml, pathlib
                                answers_path = pathlib.Path(*sys.argv[1:])
                                answers = yaml.safe_load(answers_path.read_text())
                                answers["best_song_list"] = [answers.pop("best_song")]
                                answers_path.write_text(yaml.safe_dump(answers))
                            - "[[ _copier_conf.dst_path ]]"
                            - "[[ _copier_conf.answers_file ]]"
                    """,
                "songs.yaml.tmpl": "[[ best_song_list|to_nice_yaml ]]",
            }
        )
        git("add", ".")
        git("commit", "-m2")
        git("tag", "v2")
    # User updates subproject to v2 template
    with local.cwd(subproject):
        copy(force=True)
        answers = yaml.safe_load(Path(".copier-answers.yml").read_text())
        assert answers["_commit"] == "v2"
        assert "best_song" not in answers
        assert answers["best_song_list"] == ["la vie en rose"]
        assert yaml.safe_load(Path("songs.yaml").read_text()) == ["la vie en rose"]
