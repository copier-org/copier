#!/usr/bin/env python
"""
COPY THIS FILE TO YOUR PROJECT.
---------
This file generates all the necessary files for packaging for the project.
Read more about it at https://github.com/jpscaletti/mastermold/
"""

data = {
    "title": "Copier",
    "name": "copier",
    "pypi_name": "copier",
    "version": "3.0",
    "author": "Juan-Pablo Scaletti",
    "author_email": "juanpablo@jpscaletti.com",
    "description": "A library for rendering projects templates.",
    "copyright": "2011",
    "repo_name": "jpscaletti/copier",
    "home_url": "",
    "project_urls": {},
    "development_status": "5 - Production/Stable",
    "minimal_python": 3.6,
    "install_requires": [
        "jinja2 ~= 2.10",
        "colorama ~= 0.4",
        "ruamel.yaml ~= 0.15",
        "pydantic ~= 0.30",
    ],
    "testing_requires": ["pytest", "pytest-mock", "pytest-mypy" "pytest-cov"],
    "development_requires": ["pytest-flake8", "flake8", "ipdb", "tox"],
    "entry_points": "copier = copier.cli:run",
    "coverage_omit": [],
}

exclude = [
    "copier.yml",
    "README.md",
    ".git",
    ".git/*",
    ".venv",
    ".venv/*",
    "docs",
    "docs/*",
]


def do_the_thing():
    import copier

    copier.copy(
        # "gh:jpscaletti/mastermold.git",
        "../mastermold",  # Path to the local copy of Master Mold
        ".",
        data=data,
        exclude=exclude,
        force=False,
        cleanup_on_error=False,
    )


if __name__ == "__main__":
    do_the_thing()
