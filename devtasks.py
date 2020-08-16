import shutil
from pathlib import Path


def clean():
    """
    Clean build, test or other process artefacrts from the project workspace
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
