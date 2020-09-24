"""Functions used to load user data."""

import json
import re
from collections import ChainMap
from contextlib import suppress
from pathlib import Path
from typing import (
    Any,
    Callable,
    ChainMap as t_ChainMap,
    Dict,
    Iterable,
    List,
    Optional,
    Union,
)

import yaml
from iteration_utilities import deepflatten
from jinja2 import UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.validation import Validator
from pydantic import BaseModel, Field, validator
from pygments.lexers.data import JsonLexer, YamlLexer
from PyInquirer.prompt import prompt
from yamlinclude import YamlIncludeConstructor

from ..tools import (
    cast_str_to_bool,
    force_str_end,
    get_jinja_env,
    parse_yaml_string,
    printf_exception,
)
from ..types import AnyByStrDict, OptStrOrPath, PathSeq, StrOrPath
from .objects import DEFAULT_DATA, EnvOps, UserMessageError

__all__ = ("load_config_data", "query_user_data")

CAST_STR_TO_NATIVE: Dict[str, Callable] = {
    "bool": cast_str_to_bool,
    "float": float,
    "int": int,
    "json": json.loads,
    "str": str,
    "yaml": parse_yaml_string,
}


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


class Question(BaseModel):
    choices: Union[Dict[Any, Any], List[Any]] = Field(default_factory=list)
    default: Any = None
    help_text: str = ""
    multiline: Optional[bool] = None
    placeholder: str = ""
    questionary: "Questionary"
    secret: bool = False
    type_name: str = ""
    var_name: str
    when: Union[str, bool] = True

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        # Transform arguments that are named like python keywords
        to_rename = (("help", "help_text"), ("type", "type_name"))
        for from_, to in to_rename:
            with suppress(KeyError):
                kwargs.setdefault(to, kwargs.pop(from_))
        # Infer type from default if missing
        super().__init__(**kwargs)
        self.questionary.questions.append(self)

    def __repr__(self):
        return f"Question({self.var_name})"

    @validator("var_name")
    def _check_var_name(cls, v):
        if v in DEFAULT_DATA:
            raise ValueError("Invalid question name")
        return v

    @validator("type_name", always=True)
    def _check_type_name(cls, v, values):
        if v == "":
            default_type_name = type(values.get("default")).__name__
            v = default_type_name if default_type_name in CAST_STR_TO_NATIVE else "yaml"
        if v not in CAST_STR_TO_NATIVE:
            raise InvalidTypeError("Invalid question type")
        return v

    def _iter_choices(self) -> Iterable[dict]:
        choices = self.choices
        if isinstance(self.choices, dict):
            choices = list(self.choices.items())
        for choice in choices:
            # If a choice is a dict, it can be used raw
            if isinstance(choice, dict):
                yield choice
                continue
            # However, a choice can also be a single value...
            name = value = choice
            # ... or a value pair
            if isinstance(choice, (tuple, list)):
                name, value = choice
            # The name must always be a str
            name = str(name)
            yield {"name": name, "value": value}

    def get_default(self, for_inquirer: bool) -> Any:
        cast_fn = self.get_cast_fn()
        try:
            result = self.questionary.answers_forced[self.var_name]
        except KeyError:
            try:
                result = self.questionary.answers_last[self.var_name]
            except KeyError:
                result = self.render_value(self.default)
        result = cast_answer_type(result, cast_fn)
        if not for_inquirer or self.type_name == "bool":
            return result
        if result is None:
            return ""
        else:
            return str(result)

    def get_choices(self) -> List[AnyByStrDict]:
        result = []
        for choice in self._iter_choices():
            formatted_choice = {
                key: self.render_value(value) for key, value in choice.items()
            }
            result.append(formatted_choice)
        return result

    def get_filter(self, answer) -> Any:
        if answer == self.get_default(for_inquirer=True):
            return self.get_default(for_inquirer=False)
        return cast_answer_type(answer, self.get_cast_fn())

    def get_message(self) -> str:
        message = ""
        if self.help_text:
            rendered_help = self.render_value(self.help_text)
            message = force_str_end(rendered_help)
        message += f"{self.var_name}? Format: {self.type_name}"
        return message

    def get_placeholder(self) -> str:
        return self.render_value(self.placeholder)

    def get_pyinquirer_structure(self):
        lexer = None
        result = {
            "default": self.get_default(for_inquirer=True),
            "filter": self.get_filter,
            "message": self.get_message(),
            "mouse_support": True,
            "name": self.var_name,
            "qmark": "🕵️" if self.secret else "🎤",
            "validator": Validator.from_callable(self.get_validator),
            "when": self.get_when,
        }
        multiline = self.multiline
        pyinquirer_type = "input"
        if self.type_name == "bool":
            pyinquirer_type = "confirm"
        if self.choices:
            pyinquirer_type = "list"
            result["choices"] = self.get_choices()
        if pyinquirer_type == "input":
            if self.secret:
                pyinquirer_type = "password"
            elif self.type_name == "yaml":
                lexer = PygmentsLexer(YamlLexer)
            elif self.type_name == "json":
                lexer = PygmentsLexer(JsonLexer)
        placeholder = self.get_placeholder()
        if placeholder:
            result["placeholder"] = placeholder
        multiline = multiline or (
            multiline is None and self.type_name in {"yaml", "json"}
        )
        result.update({"type": pyinquirer_type, "lexer": lexer, "multiline": multiline})
        return result

    def get_cast_fn(self) -> Callable:
        return CAST_STR_TO_NATIVE.get(self.type_name, parse_yaml_string)

    def get_validator(self, document) -> bool:
        cast_fn = self.get_cast_fn()
        try:
            cast_fn(document)
            return True
        except Exception:
            return False

    def get_when(self, answers) -> bool:
        if (
            # Skip on --force
            not self.questionary.ask_user
            # Skip on --data=this_question=some_answer
            or self.var_name in self.questionary.answers_forced
        ):
            return False
        when = self.when
        when = self.render_value(when)
        when = cast_answer_type(when, parse_yaml_string)
        return bool(when)

    def render_value(self, value: Any) -> str:
        """Render a single templated value using Jinja.

        If the value cannot be used as a template, it will be returned as is.
        """
        try:
            template = self.questionary.env.from_string(value)
        except TypeError:
            # value was not a string
            return value
        try:
            return template.render(**self.questionary.get_best_answers())
        except UndefinedError as error:
            raise UserMessageError(str(error)) from error


class Questionary(BaseModel):
    answers_forced: AnyByStrDict = Field(default_factory=dict)
    answers_last: AnyByStrDict = Field(default_factory=dict)
    answers_user: AnyByStrDict = Field(default_factory=dict)
    ask_user: bool = True
    env: SandboxedEnvironment
    questions: List[Question] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_best_answers(self) -> t_ChainMap[str, Any]:
        return ChainMap(self.answers_user, self.answers_last, self.answers_forced)

    def get_answers(self) -> AnyByStrDict:
        if self.ask_user:
            prompt(
                (question.get_pyinquirer_structure() for question in self.questions),
                answers=self.answers_user,
                raise_keyboard_interrupt=True,
            )
        else:
            previous_answers = self.get_best_answers()
            # Avoid prompting to not requiring a TTy when --force
            for question in self.questions:
                new_answer = question.get_default(for_inquirer=False)
                previous_answer = previous_answers.get(question.var_name)
                if new_answer != previous_answer:
                    self.answers_user[question.var_name] = new_answer
        return self.answers_user


Question.update_forward_refs()


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


def cast_answer_type(answer: Any, type_fn: Callable) -> Any:
    """Cast answer to expected type."""
    # Skip casting None into "None"
    if type_fn is str and answer is None:
        return answer
    # Parse correctly bools as 1, true, yes...
    if type_fn is bool and isinstance(answer, str):
        return parse_yaml_string(answer)
    try:
        return type_fn(answer)
    except (TypeError, AttributeError):
        # JSON or YAML failed because it wasn't a string; no need to convert
        return answer


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
