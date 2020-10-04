import os

from .helpers import bin_prefix, is_venv

# HACK https://github.com/microsoft/vscode-python/issues/14222
if is_venv() and bin_prefix() not in os.environ["PATH"].split(os.pathsep):
    os.environ["PATH"] = bin_prefix() + os.pathsep + os.environ["PATH"]
