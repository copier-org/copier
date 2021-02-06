"""Copier (previously known as "Voodoo")."""
from .main import Worker, run_auto, run_copy, run_update  # noqa

# Backwards compatibility
copy = run_auto


# This version is a placeholder autoupdated by poetry-dynamic-versioning
__version__ = "0.0.0"
