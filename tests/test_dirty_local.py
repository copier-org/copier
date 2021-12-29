import os
from pathlib import Path
from shutil import copytree

from plumbum import local
from plumbum.cmd import git

import copier
from copier.main import run_copy, run_update

from .helpers import DATA, PROJECT_TEMPLATE, build_file_tree, filecmp

# def perform_copy():


def test_copy(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    copytree(PROJECT_TEMPLATE, src, dirs_exist_ok=True)

    with local.cwd(src):
        git("init")

    copier.copy(str(src), str(dst), data=DATA, quiet=True)

    generated = (dst / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "reference_files/pyproject.toml").read_text()
    assert generated == control


def test_update(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            src
            / ".copier-answers.yml.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
            """,
            src
            / "copier.yml": """\
                _envops:
                    "keep_trailing_newline": True
            """,
            src
            / "aaaa.txt": """
                Lorem ipsum
            """,
        }
    )

    with local.cwd(src):
        git("init")
        git("add", ".")
        git("commit", "-am", "first commit on src")

    run_copy(str(src), dst, defaults=True, overwrite=True)

    with local.cwd(src):
        # test adding a file
        with open("test_file.txt", "w") as f:
            f.write("Test content")

        # test updating a file
        with open("aaaa.txt", "a") as f:
            f.write("dolor sit amet")

    # dst must be vcs-tracked to use run_update
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-am", "first commit on dst")

    assert not os.path.exists(dst / "test_file.txt")

    run_update(dst, defaults=True, overwrite=True)

    assert os.path.exists(dst / "test_file.txt")

    p1 = str(src / "aaaa.txt")
    p2 = str(dst / "aaaa.txt")
    assert filecmp.cmp(p1, p2)
