from pathlib import Path

from setuptools import find_packages, setup


HERE = Path(__file__).parent.resolve()

setup_data = {
    "name": "Copier",
    "version": "2.3",
    "description": "A library for rendering projects templates",
    "author": "Juan-Pablo Scaletti",
    "author_email": "juanpablo@jpscaletti.com",
    "url": "https://github.com/jpscaletti/copier",

    "long_description": (HERE / "README.md").read_text(),
    "long_description_content_type": "text/markdown",
    "python_requires": ">=3.5,<4.0",
    "install_requires": [
        "jinja2 ~= 2.10",
        "colorama ~= 0.4",
        "toml ~= 0.10",
    ],
    "license": "MIT",
    "packages": find_packages(exclude=["tests"]),
    # If your package is a single module, use this instead of "packages":
    # "py_modules": [],
    "include_package_data": True,
    "classifiers": [
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],

    "entry_points": {
        "console_scripts": ["copier = copier.cli:run", ],
    },
}

setup(**setup_data)
