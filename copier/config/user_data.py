"""Functions used to load user data."""

import re
from pathlib import Path

import yaml
from iteration_utilities import deepflatten
from yamlinclude import YamlIncludeConstructor

from ..tools import get_jinja_env, printf_exception
from ..types import AnyByStrDict, OptStrOrPath, PathSeq, StrOrPath
from .objects import EnvOps, Question, Questionary

__all__ = ("load_config_data", "query_user_data")


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


class InvalidTypeError(TypeError):
    pass


def load_yaml_data(conf_path: Path, quiet: bool = False) -> AnyByStrDict:
    """Load the `copier.yml` file.

    This is like a simple YAML load, but applying all specific quirks needed
    for [the `copier.yml` file][the-copieryml-file].

    For example, it supports the `!include` tag with glob includes, and
    merges multiple sections.

    Params:
        conf_path: The path to the `copier.yml` file.
        quiet: Used to configure the exception.

    Raises:
        InvalidConfigFileError: When the file is formatted badly.
    """
    YamlIncludeConstructor.add_to_loader_class(
        loader_class=yaml.FullLoader, base_dir=conf_path.parent
    )

    try:
        with open(conf_path) as f:
            flattened_result = deepflatten(
                yaml.load_all(f, Loader=yaml.FullLoader), depth=2, types=(list,),
            )
            # HACK https://bugs.python.org/issue32792#msg311822
            # I'd use ChainMap, but it doesn't respect order in Python 3.6
            result = {}
            for part in flattened_result:
                result.update(part)
            return result
    except yaml.parser.ParserError as e:
        raise InvalidConfigFileError(conf_path, quiet) from e


def load_config_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    """Try to load the content from a `copier.yml` or a `copier.yaml` file.
    """
    conf_paths = [
        p
        for p in Path(src_path).glob("copier.*")
        if p.is_file() and re.match(r"\.ya?ml", p.suffix, re.I)
    ]

    if len(conf_paths) > 1:
        raise MultipleConfigFilesError(conf_paths, quiet=quiet)
    elif len(conf_paths) == 1:
        return load_yaml_data(conf_paths[0], quiet=quiet)
    else:
        return {}


def load_answersfile_data(
    dst_path: StrOrPath, answers_file: OptStrOrPath = None,
) -> AnyByStrDict:
    """Load answers data from a `$dst_path/$answers_file` file if it exists."""
    try:
        with open(Path(dst_path) / (answers_file or ".copier-answers.yml")) as fd:
            return yaml.safe_load(fd)
    except FileNotFoundError:
        return {}


def query_user_data(
    questions_data: AnyByStrDict,
    last_answers_data: AnyByStrDict,
    forced_answers_data: AnyByStrDict,
    ask_user: bool,
    envops: EnvOps,
) -> AnyByStrDict:
    """Query the user for questions given in the config file."""
    questionary = Questionary(
        answers_forced=forced_answers_data,
        answers_last=last_answers_data,
        ask_user=ask_user,
        env=get_jinja_env(envops=envops),
    )
    for question, details in questions_data.items():
        Question(var_name=question, questionary=questionary, **details)
    return questionary.get_answers()
