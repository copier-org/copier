from typing import Tuple

from ..types import AnyByStrDict, OptAnyByStrDict, OptBool, OptStr, OptStrSeq
from .objects import DEFAULT_DATA, ConfigData, EnvOps, Flags, NoSrcPathError
from .user_data import load_answersfile_data, load_config_data, query_user_data

__all__ = ("make_config",)


def filter_config(data: AnyByStrDict) -> Tuple[AnyByStrDict, AnyByStrDict]:
    """Separates config and questions data."""
    conf_data = {}
    questions_data = {}
    for k, v in data.items():
        if k.startswith("_"):
            conf_data[k[1:]] = v
        else:
            # Transform simplified questions format into complex
            if not isinstance(v, dict):
                v = {"default": v}
            questions_data[k] = v
    return conf_data, questions_data


def make_config(
    src_path: OptStr = None,
    dst_path: str = ".",
    *,
    data: OptAnyByStrDict = None,
    exclude: OptStrSeq = None,
    include: OptStrSeq = None,
    skip_if_exists: OptStrSeq = None,
    tasks: OptStrSeq = None,
    envops: OptAnyByStrDict = None,
    extra_paths: OptStrSeq = None,
    pretend: OptBool = None,
    force: OptBool = None,
    skip: OptBool = None,
    quiet: OptBool = None,
    cleanup_on_error: OptBool = None,
    original_src_path: str = None,
    **kwargs,
) -> Tuple[ConfigData, Flags]:
    """Provides the configuration object, merged from the different sources.

    The order of precedence for the merger of configuration object is:
    function_args > user_data > defaults.
    """
    # Merge answer sources in the order of precedence
    answers_data = DEFAULT_DATA.copy()
    answers_data.update(load_answersfile_data(dst_path, quiet=True))
    answers_data.update(data or {})
    # Detect original source if running in update mode
    if src_path is None:
        try:
            src_path = answers_data["_src_path"]
        except KeyError:
            raise NoSrcPathError(
                "No .copier-answers.yml file found, or it didn't include "
                "original template information (_src_path). "
                "Run `copier copy` instead."
            )
        original_src_path = original_src_path or src_path
    # Obtain config and query data, asking the user if needed
    file_data = load_config_data(src_path, quiet=True)
    config_data, questions_data = filter_config(file_data)
    config_data["data"] = query_user_data(questions_data, answers_data, not force)
    args = {k: v for k, v in locals().items() if v is not None}
    args = {**config_data, **args}
    args["envops"] = EnvOps(**args.get("envops", {}))
    args["data"].update(config_data["data"])
    return ConfigData(**args), Flags(**args)
