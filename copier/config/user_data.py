"""Functions used to load user data."""

import json
import re
from collections import ChainMap
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable, ChainMap as t_ChainMap, Dict, List, Union

import yaml
from iteration_utilities import deepflatten
from jinja2 import UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from prompt_toolkit.lexers import PygmentsLexer
from pydantic import BaseModel, Field, PrivateAttr, validator
from pygments.lexers.data import JsonLexer, YamlLexer
from questionary import unsafe_prompt
from questionary.prompts.common import Choice
from yamlinclude import YamlIncludeConstructor

from ..tools import cast_str_to_bool, force_str_end, get_jinja_env, printf_exception
from ..types import AnyByStrDict, OptStrOrPath, PathSeq, StrOrPath
from .objects import DEFAULT_DATA, EnvOps, UserMessageError

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


class Question(BaseModel):
    """One question asked to the user.

    All attributes are init kwargs.

    Attributes:
        choices:
            Selections available for the user if the question requires them.
            Can be templated.

        default:
            Default value presented to the user to make it easier to respond.
            Can be templated.

        help_text:
            Additional text printed to the user, explaining the purpose of
            this question. Can be templated.

        multiline:
            Indicates if the question should allow multiline input. Defaults
            to `True` for JSON and YAML questions, and to `False` otherwise.
            Only meaningful for str-based questions. Can be templated.

        placeholder:
            Text that appears if there's nothing written in the input field,
            but disappears as soon as the user writes anything. Can be templated.

        questionary:
            Reference to the [Questionary][] object where this [Question][] is
            attached.

        secret:
            Indicates if the question should be removed from the answers file.
            If the question type is str, it will hide user input on the screen
            by displaying asterisks: `****`.

        type_name:
            The type of question. Affects the rendering, validation and filtering.
            Can be templated.

        var_name:
            Question name in the answers dict.

        when:
            Condition that, if `False`, skips the question. Can be templated.
            If it is a boolean, it is used directly. If it is a str, it is
            converted to boolean using a parser similar to YAML, but only for
            boolean values.
    """

    choices: Union[Dict[Any, Any], List[Any]] = Field(default_factory=list)
    default: Any = None
    help_text: str = ""
    multiline: Union[str, bool] = False
    placeholder: str = ""
    questionary: "Questionary"
    secret: bool = False
    type_name: str = ""
    var_name: str
    when: Union[str, bool] = True

    # Private
    _cached_choices: List[Choice] = PrivateAttr(default_factory=list)

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
        return v

    def _generate_choices(self) -> None:
        """Iterates choices in a format that the questionary lib likes."""
        if self._cached_choices:
            return
        choices = self.choices
        if isinstance(self.choices, dict):
            choices = list(self.choices.items())
        for choice in choices:
            # If a choice is a dict, it can be used raw
            if isinstance(choice, dict):
                name = choice["name"]
                value = choice["value"]
            # ... or a value pair
            elif isinstance(choice, (tuple, list)):
                name, value = choice
            # However, a choice can also be a single value...
            else:
                name = value = choice
            # The name must always be a str
            name = str(name)
            # The value can be templated
            value = self.render_value(value)
            self._cached_choices.append(Choice(name, value))

    def get_default(self) -> Any:
        """Get the default value for this question, casted to its expected type."""
        cast_fn = self.get_cast_fn()
        try:
            result = self.questionary.answers_forced[self.var_name]
        except KeyError:
            try:
                result = self.questionary.answers_last[self.var_name]
            except KeyError:
                result = self.render_value(self.default)
        result = cast_answer_type(result, cast_fn)
        return result

    def get_default_rendered(self) -> Union[bool, str, Choice, None]:
        """Get default answer rendered for the questionary lib.

        The questionary lib expects some specific data types, and returns
        it when the user answers. Sometimes you need to compare the response
        to the rendered one, or viceversa.

        This helper allows such usages.
        """
        default = self.get_default()
        # If there are choices, return the one that matches the expressed default
        if self.choices:
            for choice in self.get_choices():
                if choice.value == default:
                    return choice
            return None
        # Yes/No questions expect and return bools
        if isinstance(default, bool) and self.type_name == "bool":
            return default
        # Emptiness is expressed as an empty str
        if default is None:
            return ""
        # All other data has to be str
        return str(default)

    def get_choices(self) -> List[Choice]:
        """Obtain choices rendered and properly formatted."""
        self._generate_choices()
        return self._cached_choices

    def filter_answer(self, answer) -> Any:
        """Cast the answer to the desired type."""
        if answer == self.get_default_rendered():
            return self.get_default()
        return cast_answer_type(answer, self.get_cast_fn())

    def get_message(self) -> str:
        """Get the message that will be printed to the user."""
        message = ""
        if self.help_text:
            rendered_help = self.render_value(self.help_text)
            message = force_str_end(rendered_help)
        message += f"{self.var_name}? Format: {self.type_name}"
        return message

    def get_placeholder(self) -> str:
        """Render and obtain the placeholder."""
        return self.render_value(self.placeholder)

    def get_questionary_structure(self) -> AnyByStrDict:
        """Get the question in a format that the questionary lib understands."""
        lexer = None
        result: AnyByStrDict = {
            "default": self.get_default_rendered(),
            "filter": self.filter_answer,
            "message": self.get_message(),
            "mouse_support": True,
            "name": self.var_name,
            "qmark": "🕵️" if self.secret else "🎤",
            "when": self.get_when,
        }
        questionary_type = "input"
        if self.type_name == "bool":
            questionary_type = "confirm"
        if self.choices:
            questionary_type = "select"
            result["choices"] = self.get_choices()
        if questionary_type == "input":
            if self.secret:
                questionary_type = "password"
            elif self.type_name == "yaml":
                lexer = PygmentsLexer(YamlLexer)
            elif self.type_name == "json":
                lexer = PygmentsLexer(JsonLexer)
            if lexer:
                result["lexer"] = lexer
            result["multiline"] = self.get_multiline()
            placeholder = self.get_placeholder()
            if placeholder:
                result["placeholder"] = placeholder
            result["validate"] = self.validate_answer
        result.update({"type": questionary_type})
        return result

    def get_cast_fn(self) -> Callable:
        """Obtain function to cast user answer to desired type."""
        type_name = self.render_value(self.type_name)
        if type_name not in CAST_STR_TO_NATIVE:
            raise InvalidTypeError("Invalid question type")
        return CAST_STR_TO_NATIVE.get(type_name, parse_yaml_string)

    def get_multiline(self) -> bool:
        """Get the value for multiline."""
        multiline = self.render_value(self.multiline)
        multiline = cast_answer_type(multiline, cast_str_to_bool)
        return bool(multiline)

    def validate_answer(self, answer) -> bool:
        """Validate user answer."""
        cast_fn = self.get_cast_fn()
        try:
            cast_fn(answer)
            return True
        except Exception:
            return False

    def get_when(self, answers) -> bool:
        """Get skip condition for question."""
        if (
            # Skip on --force
            not self.questionary.ask_user
            # Skip on --data=this_question=some_answer
            or self.var_name in self.questionary.answers_forced
        ):
            return False
        when = self.when
        when = self.render_value(when)
        when = cast_answer_type(when, cast_str_to_bool)
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
            return template.render(
                **self.questionary.get_best_answers(), **DEFAULT_DATA
            )
        except UndefinedError as error:
            raise UserMessageError(str(error)) from error


class Questionary(BaseModel):
    """An object holding all [Question][] items and user answers.

    All attributes are also init kwargs.

    Attributes:
        answers_default:
            Default answers as specified in the template.

        answers_forced:
            Answers forced by the user, either by an API call like
            `data={'some_question': 'forced_answer'}` or by a CLI call like
            `--data=some_question=forced_answer`.

        answers_last:
            Answers obtained from the `.copier-answers.yml` file.

        answers_user:
            Dict containing user answers for the current questionary. It should
            be empty always.

        ask_user:
            Indicates if the questionary should be asked, or just forced.

        env:
            The Jinja environment for rendering.

        questions:
            A list containing all [Question][] objects for this [Questionary][].
    """

    # TODO Use AnsersMap instead
    answers_default: AnyByStrDict = Field(default_factory=dict)
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
        """Get dict-like object with the best answers for each question."""
        return ChainMap(
            self.answers_user,
            self.answers_last,
            self.answers_forced,
            self.answers_default,
        )

    def get_answers(self) -> AnyByStrDict:
        """Obtain answers for all questions.

        It produces a TUI for querying the user if `ask_user` is true. Otherwise,
        it gets answers from other sources.
        """
        previous_answers = self.get_best_answers()
        if self.ask_user:
            self.answers_user = unsafe_prompt(
                (question.get_questionary_structure() for question in self.questions),
                answers=previous_answers,
            )
        else:
            # Avoid prompting to not requiring a TTy when --force
            for question in self.questions:
                new_answer = question.get_default()
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
                yaml.load_all(f, Loader=yaml.FullLoader),
                depth=2,
                types=(list,),
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
    """Try to load the content from a `copier.yml` or a `copier.yaml` file."""
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
    dst_path: StrOrPath,
    answers_file: OptStrOrPath = None,
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
    try:
        return type_fn(answer)
    except (TypeError, AttributeError):
        # JSON or YAML failed because it wasn't a string; no need to convert
        return answer


CAST_STR_TO_NATIVE: Dict[str, Callable] = {
    "bool": cast_str_to_bool,
    "float": float,
    "int": int,
    "json": json.loads,
    "str": str,
    "yaml": parse_yaml_string,
}


def query_user_data(
    questions_data: AnyByStrDict,
    last_answers_data: AnyByStrDict,
    forced_answers_data: AnyByStrDict,
    default_answers_data: AnyByStrDict,
    ask_user: bool,
    envops: EnvOps,
) -> AnyByStrDict:
    """Query the user for questions given in the config file."""
    questionary = Questionary(
        answers_forced=forced_answers_data,
        answers_last=last_answers_data,
        answers_default=default_answers_data,
        ask_user=ask_user,
        env=get_jinja_env(envops=envops),
    )
    for question, details in questions_data.items():
        Question(var_name=question, questionary=questionary, **details)
    return questionary.get_answers()
