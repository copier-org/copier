from collections import ChainMap
from typing import Tuple

from packaging import version
from plumbum import local
from plumbum.cmd import git

from .. import vcs
from ..types import AnyByStrDict, OptAnyByStrDict, OptBool, OptStr, OptStrSeq
from .objects import ConfigData, EnvOps, NoSrcPathError, UserMessageError
from .user_data import load_answersfile_data, load_config_data, query_user_data

__all__ = ("make_config",)


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

    if version.parse(__version__) < version.parse(version_str):
        raise UserMessageError(
            f"This template requires Copier version >= {version_str}, "
            f"while your version of Copier is {__version__}."
        )


def make_config(
    src_path: OptStr = None,
    dst_path: str = ".",
    *,
    answers_file: OptStr = None,
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
    subdirectory: OptStr = None,
    **kwargs,
) -> ConfigData:
    """Provides the configuration object, merged from the different sources.

    The order of precedence for the merger of configuration objects is:
    function_args > user_data > defaults.
    """
    # These args are provided by API or CLI call
    init_args = {k: v for k, v in locals().items() if v is not None and v != []}
    # Store different answer sources
    init_args["data_from_answers_file"] = load_answersfile_data(dst_path, answers_file)
    if "_commit" in init_args["data_from_answers_file"]:
        init_args["old_commit"] = init_args["data_from_answers_file"]["_commit"]
    # Detect original source if running in update mode
    if src_path is None:
        try:
            src_path = init_args["data_from_answers_file"]["_src_path"]
        except KeyError:
            raise NoSrcPathError(
                "No copier answers file found, or it didn't include "
                "original template information (_src_path). "
                "Run `copier copy` instead."
            )
    init_args["original_src_path"] = src_path
    if src_path:
        repo = vcs.get_repo(src_path)
        if repo:
            src_path = vcs.clone(repo, vcs_ref or "HEAD")
            vcs_ref = vcs_ref or vcs.checkout_latest_tag(src_path)
            with local.cwd(src_path):
                init_args["commit"] = git("describe", "--tags", "--always").strip()
        init_args["src_path"] = src_path
    # Obtain config and query data, asking the user if needed
    file_data = load_config_data(src_path, quiet=True)

    try:
        verify_minimum_version(file_data["_min_copier_version"])
    except KeyError:
        pass

    template_config_data, questions_data = filter_config(file_data)
    init_args["data_from_template_defaults"] = {
        k: v.get("default") for k, v in questions_data.items()
    }
    init_args["envops"] = EnvOps(**template_config_data.get("envops", {}))
    data = kwargs.get("data") or {}
    init_args["data_from_init"] = ChainMap(
        query_user_data(
            {k: v for k, v in questions_data.items() if k in data},
            {},
            data,
            False,
            init_args["envops"],
        ),
        data,
    )
    init_args["data_from_asking_user"] = query_user_data(
        questions_data,
        init_args["data_from_answers_file"],
        init_args["data_from_init"],
        not force,
        init_args["envops"],
    )
    return ConfigData(**ChainMap(init_args, template_config_data))
