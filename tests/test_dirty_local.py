import os
from pathlib import Path
from shutil import copy2, copytree

import pytest
from plumbum import local
from plumbum.cmd import git

import copier
from copier.errors import DirtyLocalWarning
from copier.main import run_copy, run_update

from .helpers import DATA, PROJECT_TEMPLATE, build_file_tree, filecmp


def test_copy(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # dirs_exist_ok not available in Python 3.7
    for item in os.listdir(PROJECT_TEMPLATE):
        item_src_path = os.path.join(PROJECT_TEMPLATE, item)
        item_dst_path = os.path.join(src, item)
        if os.path.isdir(item_src_path):
            copytree(item_src_path, item_dst_path)
        else:
            copy2(item_src_path, item_dst_path)

    with local.cwd(src):
        git("init")

    with pytest.warns(DirtyLocalWarning):
        copier.copy(str(src), str(dst), data=DATA, quiet=True)

    generated = (dst / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "reference_files" / "pyproject.toml").read_text()
    assert generated == control

    # assert template still dirty
    with local.cwd(src):
        assert bool(git("status", "--porcelain").strip())


# Will fail due to lingering deleted file.
# HACK https://github.com/copier-org/copier/issues/461
# TODO Remove xfail decorator when fixed.
@pytest.mark.xfail(strict=True)
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
            src
            / "to_delete.txt": """
                delete me.
            """,
        }
    )

    with local.cwd(src):
        git("init")
        git("add", "-A")
        git("commit", "-m", "first commit on src")

    run_copy(str(src), dst, defaults=True, overwrite=True)

    with local.cwd(src):
        # test adding a file
        with open("test_file.txt", "w") as f:
            f.write("Test content")

        # test updating a file
        with open("aaaa.txt", "a") as f:
            f.write("dolor sit amet")

        # test removing a file
        os.remove("to_delete.txt")

    # dst must be vcs-tracked to use run_update
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "first commit on dst")

    # make sure changes have not yet propagated
    assert not os.path.exists(dst / "test_file.txt")

    p1 = str(src / "aaaa.txt")
    p2 = str(dst / "aaaa.txt")
    assert not filecmp.cmp(p1, p2)

    assert os.path.exists(dst / "to_delete.txt")

    with pytest.warns(DirtyLocalWarning):
        run_update(dst, defaults=True, overwrite=True)

    # make sure changes propagate after update
    assert os.path.exists(dst / "test_file.txt")

    p1 = str(src / "aaaa.txt")
    p2 = str(dst / "aaaa.txt")
    assert filecmp.cmp(p1, p2)

    assert not os.path.exists(dst / "to_delete.txt")
