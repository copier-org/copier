"""Functions used to load user data."""
import datetime
import json
from collections import ChainMap
from dataclasses import field
from hashlib import sha512
from os import urandom
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ChainMap as t_ChainMap,
    Dict,
    List,
    Union,
)

import yaml
from jinja2 import UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from prompt_toolkit.lexers import PygmentsLexer
from pydantic import validator
from pydantic.dataclasses import dataclass
from pygments.lexers.data import JsonLexer, YamlLexer
from questionary.prompts.common import Choice

from .errors import InvalidTypeError, UserMessageError
from .tools import cast_str_to_bool, force_str_end
from .types import AllowArbitraryTypes, AnyByStrDict, OptStr, OptStrOrPath, StrOrPath

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property

if TYPE_CHECKING:
    pass

DEFAULT_DATA: AnyByStrDict = {
    "now": datetime.datetime.utcnow,
    "make_secret": lambda: sha512(urandom(48)).hexdigest(),
}


@dataclass
class AnswersMap:
    """Object that gathers answers from different sources.

    Attributes:
        local:
            Local overrides to other answers.

        user:
            Answers provided by the user, interactively.

        init:
            Answers provided on init.

            This will hold those answers that come from `--data` in
            CLI mode.

            See [data][].

        metadata:
            Data used to be able to reproduce the template.

            It comes from [copier.template.Template.metadata][].

        last:
            Data from [the answers file][the-copier-answersyml-file].

        default:
            Default data from the template.

            See [copier.template.Template.default_answers][].
    """

    # Private
    local: AnyByStrDict = field(default_factory=dict, init=False)

    # Public
    user: AnyByStrDict = field(default_factory=dict)
    init: AnyByStrDict = field(default_factory=dict)
    metadata: AnyByStrDict = field(default_factory=dict)
    last: AnyByStrDict = field(default_factory=dict)
    default: AnyByStrDict = field(default_factory=dict)

    @cached_property
    def combined(self) -> t_ChainMap[str, Any]:
        """Answers combined from different sources, sorted by priority."""
        return ChainMap(
            self.local,
            self.user,
            self.init,
            self.metadata,
            self.last,
            self.default,
            DEFAULT_DATA,
        )

    def old_commit(self) -> OptStr:
        return self.last.get("_commit")


@dataclass(config=AllowArbitraryTypes)
class Question:
    """One question asked to the user.

    All attributes are init kwargs.

    Attributes:
        choices:
            Selections available for the user if the question requires them.
            Can be templated.

        default:
            Default value presented to the user to make it easier to respond.
            Can be templated.

        help:
            Additional text printed to the user, explaining the purpose of
            this question. Can be templated.

        multiline:
            Indicates if the question should allow multiline input. Defaults
            to `True` for JSON and YAML questions, and to `False` otherwise.
            Only meaningful for str-based questions. Can be templated.

        placeholder:
            Text that appears if there's nothing written in the input field,
            but disappears as soon as the user writes anything. Can be templated.

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

    var_name: str
    answers: AnswersMap
    jinja_env: SandboxedEnvironment
    choices: Union[Dict[Any, Any], List[Any]] = field(default_factory=list)
    default: Any = None
    help: str = ""
    ask_user: bool = False
    multiline: Union[str, bool] = False
    placeholder: str = ""
    secret: bool = False
    type: str = ""
    when: Union[str, bool] = True

    @validator("var_name")
    def _check_var_name(cls, v):
        if v in DEFAULT_DATA:
            raise ValueError("Invalid question name")
        return v

    @validator("type", always=True)
    def _check_type(cls, v, values):
        if v == "":
            default_type_name = type(values.get("default")).__name__
            v = default_type_name if default_type_name in CAST_STR_TO_NATIVE else "yaml"
        return v

    def get_default(self) -> Any:
        """Get the default value for this question, casted to its expected type."""
        cast_fn = self.get_cast_fn()
        try:
            result = self.answers.init[self.var_name]
        except KeyError:
            try:
                result = self.answers.last[self.var_name]
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
            for choice in self._formatted_choices:
                if choice.value == default:
                    return choice
            return None
        # Yes/No questions expect and return bools
        if isinstance(default, bool) and self.type == "bool":
            return default
        # Emptiness is expressed as an empty str
        if default is None:
            return ""
        # All other data has to be str
        return str(default)

    @cached_property
    def _formatted_choices(self) -> List[Choice]:
        """Obtain choices rendered and properly formatted."""
        result = []
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
            result.append(Choice(name, value))
        return result

    def filter_answer(self, answer) -> Any:
        """Cast the answer to the desired type."""
        if answer == self.get_default_rendered():
            return self.get_default()
        return cast_answer_type(answer, self.get_cast_fn())

    def get_message(self) -> str:
        """Get the message that will be printed to the user."""
        message = ""
        if self.help:
            rendered_help = self.render_value(self.help)
            message = force_str_end(rendered_help)
        message += f"{self.var_name}? Format: {self.type}"
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
        if self.type == "bool":
            questionary_type = "confirm"
        if self.choices:
            questionary_type = "select"
            result["choices"] = self._formatted_choices
        if questionary_type == "input":
            if self.secret:
                questionary_type = "password"
            elif self.type == "yaml":
                lexer = PygmentsLexer(YamlLexer)
            elif self.type == "json":
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
        type_name = self.render_value(self.type)
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
            not self.ask_user
            # Skip on --data=this_question=some_answer
            or self.var_name in self.answers.init
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
            template = self.jinja_env.from_string(value)
        except TypeError:
            # value was not a string
            return value
        try:
            return template.render(**self.answers.combined)
        except UndefinedError as error:
            raise UserMessageError(str(error)) from error


def parse_yaml_string(string: str) -> Any:
    """Parse a YAML string and raise a ValueError if parsing failed.

    This method is needed because :meth:`prompt` requires a ``ValueError``
    to repeat falied questions.
    """
    try:
        return yaml.safe_load(string)
    except yaml.error.YAMLError as error:
        raise ValueError(str(error))


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
