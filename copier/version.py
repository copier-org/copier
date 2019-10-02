import pkg_resources

try:
    __version__: str = pkg_resources.require("copier")[0].version
except Exception:  # pragma: no cover
    # Run pytest without needing to install the library
    __version__ = None  # type: ignore
