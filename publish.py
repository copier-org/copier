from pathlib import Path
from shutil import rmtree
import subprocess


HERE = Path(__file__).parent.resolve()


def call(cmd):
    return subprocess.check_call(cmd, shell=True)


def publish():
    import twine  # noqa
    import wheel  # noqa

    from copier import __version__

    try:
        print("Removing previous builds…")
        rmtree(str(HERE / "dist"))
    except OSError:
        pass

    print("Building Source and Wheel distribution…")
    call("python setup.py sdist bdist_wheel")

    print("Uploading the package to PyPI…")
    call("twine upload dist/*")

    print("Pushing git tags…")
    call("git tag v{0}".format(__version__))
    call("git push --tags")


if __name__ == "__main__":
    publish()
