"""Functions used to generate configuration data."""

from typing import Tuple

from packaging import version

from ..errors import UnsupportedVersionError
from ..types import AnyByStrDict


def filter_config(data: AnyByStrDict) -> Tuple[AnyByStrDict, AnyByStrDict]:
    """Separates config and questions data."""
    conf_data: AnyByStrDict = {"secret_questions": set()}
    questions_data = {}
    for k, v in data.items():
        if k == "_secret_questions":
            conf_data["secret_questions"].update(v)
        elif k.startswith("_"):
            conf_data[k[1:]] = v
        else:
            # Transform simplified questions format into complex
            if not isinstance(v, dict):
                v = {"default": v}
            questions_data[k] = v
            if v.get("secret"):
                conf_data["secret_questions"].add(k)
    return conf_data, questions_data


def verify_minimum_version(version_str: str) -> None:
    """Raise an error if the current Copier version is less than the given version."""
    # Importing __version__ at the top of the module creates a circular import
    # ("cannot import name '__version__' from partially initialized module 'copier'"),
    # so instead we do a lazy import here
    from .. import __version__

    # Disable check when running copier as editable installation
    if __version__ == "0.0.0":
        return

    if version.parse(__version__) < version.parse(version_str):
        raise UnsupportedVersionError(
            f"This template requires Copier version >= {version_str}, "
            f"while your version of Copier is {__version__}."
        )
