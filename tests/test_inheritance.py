from pathlib import Path

import copier


DEMO_FOLDER = Path("tests/demo_inheritance")
CHILD_DIR = DEMO_FOLDER / "child"
PARENT_DIR = DEMO_FOLDER / "parent"


def test_inheritance_single_level(dst):
    copier.copy(str(CHILD_DIR), dst, force=True)

    dst_path = Path(dst)
    assert (dst_path / "child.txt").exists()
    assert (dst_path / "parent.txt").exists()

    overwrite_me_txt = dst_path / "overwrite_me.txt"
    assert overwrite_me_txt.exists()
    assert overwrite_me_txt.read_text().strip() == "OVERRIDDEN CONTENT"
