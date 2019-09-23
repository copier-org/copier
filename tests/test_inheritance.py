from pathlib import Path

import pytest

import copier


DEMO_FOLDER = Path("tests/demo_inheritance")


def test_inheritance_single_level(dst):
    src_path = DEMO_FOLDER / "single_level" / "child"
    copier.copy(str(src_path), dst)

    assert (Path(dst) / "child.txt").exists()
    assert (Path(dst) / "parent.txt").exists()


def test_inheritance_multi_level(dst):
    src_path = DEMO_FOLDER / "multi_level" / "child"
    copier.copy(str(src_path), dst)

    assert (Path(dst) / "child.txt").exists()
    assert (Path(dst) / "parent.txt").exists()
    assert (Path(dst) / "grandparent.txt").exists()


@pytest.mark.parametrize(
    "opts, expected",
    (
        ({"force": True}, "OVERRIDDEN CONTENT"),
        ({"skip": True}, "ORIGINAL CONTENT"),
    ),
)
def test_inheritance_conflicted(dst, opts, expected):
    src_path = DEMO_FOLDER / "conflicted" / "child"
    copier.copy(str(src_path), dst, **opts)

    overwrite_me_txt = Path(dst) / "overwrite_me.txt"
    assert overwrite_me_txt.exists()
    assert overwrite_me_txt.read_text().strip() == expected


def test_inheritance_tasks(dst):
    src_path = DEMO_FOLDER / "tasks" / "child"
    copier.copy(str(src_path), dst)

    touched_by_child_txt = Path(dst) / "touched_by_child.txt"
    touched_by_parent_txt = Path(dst) / "touched_by_parent.txt"
    assert touched_by_child_txt.exists()
    assert touched_by_parent_txt.exists()
    # assert parent tasks ran before child tasks
    assert touched_by_parent_txt.stat().st_ctime < touched_by_child_txt.stat().st_ctime
