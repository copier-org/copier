from typing import Tuple

from plumbum import local
from plumbum.cmd import git

from .. import vcs
from ..types import AnyByStrDict, OptAnyByStrDict, OptBool, OptStr, OptStrSeq
from .objects import DEFAULT_DATA, ConfigData, EnvOps, NoSrcPathError
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
    skip_if_exists: OptStrSeq = None,
    tasks: OptStrSeq = None,
    envops: OptAnyByStrDict = None,
    extra_paths: OptStrSeq = None,
    pretend: OptBool = None,
    force: OptBool = None,
    skip: OptBool = None,
    quiet: OptBool = None,
    cleanup_on_error: OptBool = None,
    vcs_ref: OptStr = None,
    **kwargs,
) -> ConfigData:
    """Provides the configuration object, merged from the different sources.

    The order of precedence for the merger of configuration object is:
    function_args > user_data > defaults.
    """
    # Merge answer sources in the order of precedence
    answers_data = DEFAULT_DATA.copy()
    answers_data.update(load_answersfile_data(dst_path, quiet=True))
    answers_data.update(data or {})
    _metadata = {}
    if "_commit" in answers_data:
        _metadata["old_commit"] = answers_data["_commit"]
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
    _metadata["original_src_path"] = src_path
    if src_path:
        repo = vcs.get_repo(src_path)
        if repo:
            src_path = vcs.clone(repo, vcs_ref or "HEAD")
            vcs_ref = vcs_ref or vcs.checkout_latest_tag(src_path)
            with local.cwd(src_path):
                _metadata["commit"] = git("describe", "--tags", "--always").strip()
    # Obtain config and query data, asking the user if needed
    file_data = load_config_data(src_path, quiet=True)
    config_data, questions_data = filter_config(file_data)
    config_data.update(_metadata)
    del _metadata
    config_data["data"] = query_user_data(questions_data, answers_data, not force)
    args = {k: v for k, v in locals().items() if v is not None and v != []}
    args = {**config_data, **args}
    args["envops"] = EnvOps(**args.get("envops", {}))
    args["data"].update(config_data["data"])
    return ConfigData(**args)
