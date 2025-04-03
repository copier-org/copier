"""Copier.

Docs: https://copier.readthedocs.io/
"""

import importlib.metadata

from ._main import *  # noqa: F401,F403

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"
