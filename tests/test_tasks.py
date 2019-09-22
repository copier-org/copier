import copier

from .helpers import DATA, render


def test_render_tasks(dst):
    tasks = ["touch [[ myvar ]]/1.txt", "touch [[ myvar ]]/2.txt"]
    render(dst, tasks=tasks)
    assert (dst / DATA["myvar"] / "1.txt").exists()
    assert (dst / DATA["myvar"] / "2.txt").exists()


def test_copy_tasks(dst):
    copier.copy("tests/demo_tasks", dst, quiet=True)
    assert (dst / "hello").exists()
    assert (dst / "hello").is_dir()
    assert (dst / "hello" / "world").exists()
