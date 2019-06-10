import pkg_resources


try:
    __version__ = pkg_resources.require("copier")[0].version
except Exception:
    # Run pytest without needing to install copier
    __version__ = None
