import copier

from .helpers import DATA, render


def test_render_tasks(tmp_path):
    tasks = ["touch [[ myvar ]]/1.txt", "touch [[ myvar ]]/2.txt"]
    render(tmp_path, tasks=tasks)
    assert (tmp_path / DATA["myvar"] / "1.txt").exists()
    assert (tmp_path / DATA["myvar"] / "2.txt").exists()


def test_copy_tasks(tmp_path):
    copier.copy("tests/demo_tasks", tmp_path, quiet=True)
    assert (tmp_path / "hello").exists()
    assert (tmp_path / "hello").is_dir()
    assert (tmp_path / "hello" / "world").exists()
