import os
import shutil
from pathlib import Path
from subprocess import check_call


def clean():
    """
    Clean build, test or other process artefacts from the project workspace
    """
    build_artefacts = (
        "build/",
        "dist/",
        "*.egg-info",
        "pip-wheel-metadata",
    )
    python_artefacts = (
        ".pytest_cache",
        "htmlcov",
        ".coverage",
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
    )
    project_dir = Path(".").resolve()
    for pattern in build_artefacts + python_artefacts:
        for matching_path in project_dir.glob(pattern):
            print(f"Deleting {matching_path}")
            if matching_path.is_dir():
                shutil.rmtree(matching_path)
            else:
                matching_path.unlink()


def dev_setup():
    """Setup a development environment."""
    # Gitpod sets PIP_USER=yes, which breaks poetry
    env = dict(os.environ, PIP_USER="no")
    check_call(["poetry", "install", "--with", "docs"], env=env)
    check_call(
        [
            "poetry",
            "run",
            "pre-commit",
            "install",
            "-t",
            "pre-commit",
            "-t",
            "commit-msg",
        ],
        env=env,
    )
    check_call(["poetry", "run", "pre-commit", "install-hooks"], env=env)
