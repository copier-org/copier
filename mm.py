#!/usr/bin/env python
"""
COPY THIS FILE TO YOUR PROJECT.
---------
This file generates all the necessary files for packaging for the project.
Read more about it at https://github.com/jpscaletti/mastermold/
"""
from pathlib import Path

import copier
from ruamel.yaml import YAML


data = {
    "title": "Copier",
    "name": "copier",
    "pypi_name": "copier",
    "version": "2.4.2",
    "author": "Juan-Pablo Scaletti",
    "author_email": "juanpablo@jpscaletti.com",
    "description": "A library for rendering projects templates",
    "repo_name": "jpscaletti/copier",
    "home_url": "",
    "docs_url": "",
    "development_status": "5 - Production/Stable",
    "minimal_python": 3.5,
    "install_requires": [
        "jinja2 ~= 2.10",
        "colorama ~= 0.4",
        "toml ~= 0.10",
        "ruamel.yaml ~= 0.15",
    ],
    "test_requires": [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-flake8",
        "flake8",
        "ipdb",
        "tox",
    ],
    "entry_points": "copier = copier.cli:run",

    "coverage_omit": [],

    "copyright": "2011",
    "has_docs": False,
    "google_analytics": "UA-XXXXXXXX-X",
    "docs_nav": [],
}


def save_current_nav():
    yaml = YAML()
    mkdocs_path = Path("docs") / "mkdocs.yml"
    if not mkdocs_path.exists():
        return
    mkdocs = yaml.load(mkdocs_path)
    data["docs_nav"] = mkdocs.get("nav")


def do_the_thing():
    if data["has_docs"]:
        save_current_nav()

    copier.copy(
        "gh:jpscaletti/mastermold.git",
        ".",
        data=data,
        exclude=[
            "copier.yml",
            "README.md",
            ".git",
            ".git/*",
            ".venv",
            ".venv/*",

            "docs",
            "docs/*",
        ],
        force=True,
        cleanup_on_error=False
    )


if __name__ == "__main__":
    do_the_thing()
