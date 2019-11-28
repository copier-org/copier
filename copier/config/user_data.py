from pathlib import Path
from os.path import isfile
import re

from ..tools import HLINE, INDENT, printf_exception, prompt
from ..types import AnyByStrDict, StrOrPath, PathSeq

__all__ = ("load_config_data", "query_user_data",)


class ConfigFileError(ValueError):
    pass


class InvalidConfigFileError(ConfigFileError):
    def __init__(self, conf_path: Path, quiet: bool):
        msg = str(conf_path)
        printf_exception(self, "INVALID CONFIG FILE", msg=msg, quiet=quiet)
        super().__init__(msg)


class MultipleConfigFilesError(ConfigFileError):
    def __init__(self, conf_paths: PathSeq, quiet: bool):
        msg = str(conf_paths)
        printf_exception(self, "MULTIPLE CONFIG FILES", msg=msg, quiet=quiet)
        super().__init__(msg)


class AnswerFileError(ValueError):
    pass


class MultipleAnswerFilesError(AnswerFileError):
    def __init__(self, conf_paths: PathSeq, quiet: bool):
        msg = str(conf_paths)
        printf_exception(self, "MULTIPLE ANSWER FILES", msg=msg, quiet=quiet)
        super().__init__(msg)


def load_yaml_data(
    conf_path: Path, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    from ruamel.yaml import YAML, YAMLError

    yaml = YAML(typ="safe")

    try:
        return dict(yaml.load(conf_path))
    except YAMLError as e:
        raise InvalidConfigFileError(conf_path, quiet) from e


def load_config_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    """Try to load the content from a `copier.yml` or a `copier.yaml` file.
    """
    conf_paths = [
        p for p in Path(src_path).glob("copier.*")
        if p.is_file() and re.match(r"\.ya?ml", p.suffix, re.I)
    ]

    if len(conf_paths) > 1:
        raise MultipleConfigFilesError(conf_paths, quiet=quiet)
    elif len(conf_paths) == 1:
        return load_yaml_data(conf_paths[0], quiet=quiet, _warning=_warning)
    else:
        return {}


def load_logfile_data(
    dst_path: StrOrPath,
    *,
    quiet: bool = False,
    _warning: bool = True
) -> AnyByStrDict:
    """Load answers data from a `$dst_path/.copier-answers.yml` file if it exists.

    `.yaml` suffix is also supported.
    """
    answer_paths = list(filter(
        isfile,
        map(lambda suffix: Path(dst_path) / f".copier-answers.{suffix}", ("yml", "yaml")),
    ))
    answers_data: AnyByStrDict = {}
    if len(answer_paths) > 1:
        raise MultipleAnswerFilesError(answer_paths, quiet=quiet)
    elif len(answer_paths) == 1:
        answers_data = load_yaml_data(answer_paths[0], quiet=quiet, _warning=_warning)
    return answers_data


def query_user_data(default_user_data: AnyByStrDict) -> AnyByStrDict:  # pragma: no cover
    """Query to user about the data of the config file.
    """
    if not default_user_data:
        return {}
    print("")
    user_data = {}
    for key in default_user_data:
        default = default_user_data[key]
        user_data[key] = prompt(INDENT + f" {key}?", default)

    print(f"\n {INDENT} {HLINE}")
    return user_data
