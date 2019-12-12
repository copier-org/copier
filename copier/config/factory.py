from typing import Tuple

from ..types import AnyByStrDict, OptAnyByStrDict, OptBool, OptStr, OptStrSeq
from .objects import DEFAULT_DATA, ConfigData, EnvOps, Flags, NoSrcPathError
from .user_data import load_config_data, load_logfile_data, query_user_data

__all__ = ("make_config",)


def filter_config(data: AnyByStrDict) -> Tuple[AnyByStrDict, AnyByStrDict]:
    """Separates config and query data."""
    conf_data = {}
    query_data = {}
    for k, v in data.items():
        if k.startswith("_"):
            conf_data[k[1:]] = v
        else:
            query_data[k] = v
    return conf_data, query_data


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
    answers_data = load_logfile_data(dst_path, quiet=True)
    if src_path is None:
        try:
            src_path = answers_data["_src_path"]
            original_src_path = original_src_path or src_path
        except KeyError:
            raise NoSrcPathError(
                "No .copier-answers.yml file found, or it didn't include "
                "original template information (_src_path). "
                "Run `copier copy` instead."
            )
    file_data = load_config_data(src_path, quiet=True)
    config_data, query_data = filter_config(file_data)
    query_data.update(filter(lambda item: item[0] in query_data, answers_data.items()))

    if not force:
        query_data = query_user_data(query_data)

    # merge config sources in the order of precedence
    config_data["data"] = {**DEFAULT_DATA.copy(), **query_data, **(data or {})}

    args = {k: v for k, v in locals().items() if v is not None}
    args = {**config_data, **args}
    args["envops"] = EnvOps(**args.get("envops", {}))

    return ConfigData(**args), Flags(**args)
