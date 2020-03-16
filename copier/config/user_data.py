import json
import re
from pathlib import Path
from typing import Any, Callable, Dict

import yaml
from plumbum.cli.terminal import ask, choose, prompt
from plumbum.colors import bold, info, italics
from yamlinclude import YamlIncludeConstructor

from ..tools import INDENT, printf_exception
from ..types import AnyByStrDict, OptStrOrPath, PathSeq, StrOrPath

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


def load_yaml_data(
    conf_path: Path, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:

    YamlIncludeConstructor.add_to_loader_class(
        loader_class=yaml.FullLoader, base_dir=conf_path.parent
    )

    try:
        with open(conf_path) as f:
            return yaml.load(f, Loader=yaml.FullLoader)
    except yaml.parser.ParserError as e:
        raise InvalidConfigFileError(conf_path, quiet) from e


def parse_yaml_string(string: str) -> Any:
    """Parse a YAML string and raise a ValueError if parsing failed.

    This method is needed because :meth:`prompt` requires a ``ValueError``
    to repeat falied questions.
    """
    try:
        return yaml.safe_load(string)
    except yaml.error.YAMLError as error:
        raise ValueError(str(error))


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
        return load_yaml_data(conf_paths[0], quiet=quiet, _warning=_warning)
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
    questions_data: AnyByStrDict, answers_data: AnyByStrDict, ask_user: bool
) -> AnyByStrDict:
    """Query the user for questions given in the config file."""
    type_maps: Dict[str, Callable] = {
        "bool": bool,
        "float": float,
        "int": int,
        "json": json.loads,
        "str": str,
        "yaml": parse_yaml_string,
    }
    result: AnyByStrDict = {}
    for question, details in questions_data.items():
        # Get default answer
        default = answers_data.get(question, details.get("default"))
        # Get question type; by default let YAML decide it
        type_name = details.get("type", "yaml")
        try:
            type_fn = type_maps[type_name]
        except KeyError:
            raise InvalidTypeError()
        if not ask_user:
            # Skip casting None into "None"
            if type_name == "str" and default is None:
                result[question] = default
                continue
            # Parse correctly bools as 1, true, yes...
            if type_name == "bool" and isinstance(default, str):
                default = parse_yaml_string(default)
            try:
                result[question] = type_fn(default)
            except (TypeError, AttributeError):
                # JSON or YAML failed because it wasn't a string; no need to convert
                result[question] = default
            continue
        # Generate message to ask the user
        message = f"\n{INDENT}{bold | question}? Format: {type_name}\n🎤 "
        if details.get("help"):
            message = f"{info & italics | details['help']}\n{message}"
        # Use the right method to ask
        if type_fn == bool:
            result[question] = ask(message, default)
        elif details.get("choices"):
            result[question] = choose(message, details["choices"], default)
        else:
            result[question] = prompt(message, type_fn, default)
    return result
