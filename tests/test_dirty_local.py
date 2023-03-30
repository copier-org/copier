from pathlib import Path
from shutil import copy2, copytree

import pytest
from plumbum import local
from plumbum.cmd import git

import copier
from copier.errors import DirtyLocalWarning
from copier.main import run_copy, run_update

from .helpers import DATA, PROJECT_TEMPLATE, build_file_tree


def test_copy(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    # dirs_exist_ok not available in Python 3.7
    for item in PROJECT_TEMPLATE.iterdir():
        item_src_path = item
        item_dst_path = src / item.name
        if item_src_path.is_dir():
            copytree(item_src_path, item_dst_path)
        else:
            copy2(item_src_path, item_dst_path)

    with local.cwd(src):
        git("init")

    with pytest.warns(DirtyLocalWarning):
        copier.copy(str(src), dst, data=DATA, quiet=True)

    generated = (dst / "pyproject.toml").read_text()
    control = (Path(__file__).parent / "reference_files" / "pyproject.toml").read_text()
    assert generated == control

    # assert template still dirty
    with local.cwd(src):
        assert bool(git("status", "--porcelain").strip())


def test_update(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (src / "copier.yml"): (
                """\
                _envops:
                    "keep_trailing_newline": True
                """
            ),
            (src / "aaaa.txt"): (
                """
                Lorem ipsum
                """
            ),
            (src / "to_delete.txt"): (
                """
                delete me.
                """
            ),
        }
    )

    with local.cwd(src):
        git("init")
        git("add", "-A")
        git("commit", "-m", "first commit on src")

    run_copy(str(src), dst, defaults=True, overwrite=True)

    with local.cwd(src):
        # test adding a file
        Path("test_file.txt").write_text("Test content")

        # test updating a file
        with open("aaaa.txt", "a") as f:
            f.write("dolor sit amet")

        # test removing a file
        Path("to_delete.txt").unlink()

    # dst must be vcs-tracked to use run_update
    with local.cwd(dst):
        git("init")
        git("add", "-A")
        git("commit", "-m", "first commit on dst")

    # make sure changes have not yet propagated
    assert not (dst / "test_file.txt").exists()

    assert (src / "aaaa.txt").read_text() != (dst / "aaaa.txt").read_text()

    assert (dst / "to_delete.txt").exists()

    with pytest.warns(DirtyLocalWarning):
        run_update(dst, defaults=True, overwrite=True)

    # make sure changes propagate after update
    assert (dst / "test_file.txt").exists()

    assert (src / "aaaa.txt").read_text() == (dst / "aaaa.txt").read_text()

    # HACK https://github.com/copier-org/copier/issues/461
    # TODO test file deletion on update
    # assert not (dst / "to_delete.txt").exists()
