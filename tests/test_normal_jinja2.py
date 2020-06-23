import copier

from .helpers import PROJECT_TEMPLATE


def test_normal_jinja2(tmp_path):
    copier.copy(f"{PROJECT_TEMPLATE}_normal_jinja2", tmp_path, force=True)
    todo = (tmp_path / "TODO.txt").read_text()
    expected = "[[ Guybrush TODO LIST]]\n[# GROG #]\n    - Become a pirate\n"
    assert todo == expected
