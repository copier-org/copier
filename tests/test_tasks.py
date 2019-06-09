from .. import copier


def test_execute_tasks(dst):
    copier.copy("tests/demo_tasks", dst, quiet=True)
    assert (dst / "hello").exists()
    assert (dst / "hello").is_dir()
    assert (dst / "hello" / "world").exists()
