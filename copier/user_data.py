"""Functions used to load user data."""
import json
import sys
import warnings
from collections import ChainMap
from dataclasses import field
from datetime import datetime
from hashlib import sha512
from os import urandom
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Set,
    Union,
)

import yaml
from jinja2 import UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.validation import ValidationError
from pydantic import validator as pydantic_validator
from pydantic.dataclasses import dataclass
from pygments.lexers.data import JsonLexer, YamlLexer
from questionary.prompts.common import Choice

from .errors import InvalidTypeError, UserMessageError
from .tools import cast_str_to_bool, force_str_end
from .types import (
    MISSING,
    AllowArbitraryTypes,
    AnyByStrDict,
    MissingType,
    OptStr,
    OptStrOrPath,
    StrOrPath,
)

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property

if TYPE_CHECKING:
    pass


# TODO Remove these two functions as well as DEFAULT_DATA in a future release
def _now():
    warnings.warn(
        "'now' will be removed in a future release of Copier.\n"
        "Please use this instead: {{ '%Y-%m-%d %H:%M:%S' | strftime }}\n"
        "strftime format reference https://strftime.org/",
        FutureWarning,
    )
    return datetime.utcnow()


def _make_secret():
    warnings.warn(
        "'make_secret' will be removed in a future release of Copier.\n"
        "Please use this instead: {{ 999999999999999999999999999999999|ans_random|hash('sha512') }}\n"
        "random and hash filters documentation: https://docs.ansible.com/ansible/2.3/playbooks_filters.html",
        FutureWarning,
    )
    return sha512(urandom(48)).hexdigest()


DEFAULT_DATA: AnyByStrDict = {
    "now": _now,
    "make_secret": _make_secret,
}


@dataclass
class AnswersMap:
    """Object that gathers answers from different sources.

    Attributes:
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

        user_defaults:
            Default data from the user e.g. previously completed and restored data.

            See [copier.main.Worker][].
    """

    # Private
    hidden: Set[str] = field(default_factory=set, init=False)

    # Public
    user: AnyByStrDict = field(default_factory=dict)
    init: AnyByStrDict = field(default_factory=dict)
    metadata: AnyByStrDict = field(default_factory=dict)
    last: AnyByStrDict = field(default_factory=dict)
    user_defaults: AnyByStrDict = field(default_factory=dict)

    @property
    def combined(self) -> Mapping[str, Any]:
        """Answers combined from different sources, sorted by priority."""
        return dict(
            ChainMap(
                self.user,
                self.init,
                self.metadata,
                self.last,
                self.user_defaults,
                DEFAULT_DATA,
            )
        )

    def old_commit(self) -> OptStr:
        """Commit when the project was updated from this template the last time."""
        return self.last.get("_commit")

    def hide(self, key: str) -> None:
        """Remove an answer by key."""
        self.hidden.add(key)


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

        validator:
            Jinja template with which to validate the user input. This template
            will be rendered with the combined answers as variables; it should
            render *nothing* if the value is valid, and an error message to show
            to the user otherwise.

        when:
            Condition that, if `False`, skips the question. Can be templated.
            If it is a boolean, it is used directly. If it is a str, it is
            converted to boolean using a parser similar to YAML, but only for
            boolean values.
    """

    var_name: str
    answers: AnswersMap
    jinja_env: SandboxedEnvironment
    choices: Union[Sequence[Any], Dict[Any, Any]] = field(default_factory=list)
    default: Any = MISSING
    help: str = ""
    multiline: Union[str, bool] = False
    placeholder: str = ""
    secret: bool = False
    type: str = ""
    validator: str = ""
    when: Union[str, bool] = True

    @pydantic_validator("var_name")
    def _check_var_name(cls, v):
        if v in DEFAULT_DATA:
            raise ValueError("Invalid question name")
        return v

    @pydantic_validator("type", always=True)
    def _check_type(cls, v, values):
        if v == "":
            default_type_name = type(values.get("default")).__name__
            v = default_type_name if default_type_name in CAST_STR_TO_NATIVE else "yaml"
        return v

    def cast_answer(self, answer: Any) -> Any:
        """Cast answer to expected type."""
        type_name = self.get_type_name()
        type_fn = CAST_STR_TO_NATIVE[type_name]
        # Only JSON or YAML questions support `None` as an answer
        if answer is None and type_name not in {"json", "yaml"}:
            raise InvalidTypeError(
                f'Invalid answer "{answer}" of type "{type(answer)}" '
                f'to question "{self.var_name}" of type "{type_name}"'
            )
        try:
            return type_fn(answer)
        except (TypeError, AttributeError) as error:
            # JSON or YAML failed because it wasn't a string; no need to convert
            if type_name in {"json", "yaml"}:
                return answer
            raise InvalidTypeError from error

    def get_default(self) -> Any:
        """Get the default value for this question, casted to its expected type."""
        try:
            result = self.answers.init[self.var_name]
        except KeyError:
            try:
                result = self.answers.last[self.var_name]
            except KeyError:
                try:
                    result = self.answers.user_defaults[self.var_name]
                except KeyError:
                    if self.default is MISSING:
                        return MISSING
                    result = self.render_value(self.default)
        result = self.cast_answer(result)
        return result

    def get_default_rendered(self) -> Union[bool, str, Choice, None, MissingType]:
        """Get default answer rendered for the questionary lib.

        The questionary lib expects some specific data types, and returns
        it when the user answers. Sometimes you need to compare the response
        to the rendered one, or viceversa.

        This helper allows such usages.
        """
        default = self.get_default()
        if default is MISSING:
            return MISSING
        # If there are choices, return the one that matches the expressed default
        if self.choices:
            for choice in self._formatted_choices:
                if choice.value == default:
                    return choice
            return None
        # Yes/No questions expect and return bools
        if isinstance(default, bool) and self.get_type_name() == "bool":
            return default
        # Emptiness is expressed as an empty str
        if default is None:
            return ""
        # JSON and YAML dumped depending on multiline setting
        if self.get_type_name() == "json":
            return json.dumps(default, indent=2 if self.get_multiline() else None)
        if self.get_type_name() == "yaml":
            return yaml.safe_dump(
                default, default_flow_style=not self.get_multiline(), width=2147483647
            ).strip()
        # All other data has to be str
        return str(default)

    @cached_property
    def _formatted_choices(self) -> Sequence[Choice]:
        """Obtain choices rendered and properly formatted."""
        result = []
        choices = self.choices
        if isinstance(self.choices, dict):
            choices = list(self.choices.items())
        for choice in choices:
            # If a choice is a value pair
            if isinstance(choice, (tuple, list)):
                name, value = choice
            # If a choice is a single value
            else:
                name = value = choice
            # The name must always be a str
            name = str(self.render_value(name))
            # Extract the extended syntax for dict-like (dict-style or
            # tuple-style) choices if applicable
            disabled = ""
            if isinstance(choice, (tuple, list)) and isinstance(value, dict):
                if "value" not in value:
                    raise KeyError("Property 'value' is required")
                if "validator" in value and not isinstance(value["validator"], str):
                    raise ValueError("Property 'validator' must be a string")
                disabled = self.render_value(value.get("validator", ""))
                value = value["value"]
            # The value can be templated
            value = self.render_value(value)
            c = Choice(name, value, disabled=disabled)
            # Try to cast the value according to the question's type to raise
            # an error in case the value is incompatible.
            self.cast_answer(c.value)
            result.append(c)
        return result

    def get_message(self) -> str:
        """Get the message that will be printed to the user."""
        if self.help:
            rendered_help = self.render_value(self.help)
            if rendered_help:
                return force_str_end(rendered_help) + "  "
        # Otherwise, there's no help message defined.
        message = self.var_name
        answer_type = self.get_type_name()
        if answer_type != "str":
            message += f" ({answer_type})"
        return message + "\n  "

    def get_placeholder(self) -> str:
        """Render and obtain the placeholder."""
        return self.render_value(self.placeholder)

    def get_questionary_structure(self) -> AnyByStrDict:
        """Get the question in a format that the questionary lib understands."""
        lexer = None
        result: AnyByStrDict = {
            "filter": self.cast_answer,
            "message": self.get_message(),
            "mouse_support": True,
            "name": self.var_name,
            "qmark": "🕵️" if self.secret else "🎤",
            "when": lambda _: self.get_when(),
        }
        default = self.get_default_rendered()
        if default is not MISSING:
            result["default"] = default
        questionary_type = "input"
        type_name = self.get_type_name()
        if type_name == "bool":
            questionary_type = "confirm"
            # For backwards compatibility
            if default is MISSING:
                result["default"] = False
        if self.choices:
            questionary_type = "select"
            result["choices"] = self._formatted_choices
        if questionary_type == "input":
            if self.secret:
                questionary_type = "password"
            elif type_name == "yaml":
                lexer = PygmentsLexer(YamlLexer)
            elif type_name == "json":
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

    def get_type_name(self) -> str:
        """Render the type name and return it."""
        type_name = self.render_value(self.type)
        if type_name not in CAST_STR_TO_NATIVE:
            raise InvalidTypeError(
                f'Unsupported type "{type_name}" in question "{self.var_name}"'
            )
        return type_name

    def get_multiline(self) -> bool:
        """Get the value for multiline."""
        return cast_str_to_bool(self.render_value(self.multiline))

    def validate_answer(self, answer) -> bool:
        """Validate user answer."""
        try:
            ans = self.parse_answer(answer)
        except Exception:
            return False

        try:
            err_msg = self.render_value(self.validator, {self.var_name: ans}).strip()
        except Exception as error:
            raise ValidationError(message=str(error)) from error
        if err_msg:
            raise ValidationError(message=err_msg)
        return True

    def get_when(self) -> bool:
        """Get skip condition for question."""
        return cast_str_to_bool(self.render_value(self.when))

    def render_value(
        self, value: Any, extra_answers: Optional[AnyByStrDict] = None
    ) -> str:
        """Render a single templated value using Jinja.

        If the value cannot be used as a template, it will be returned as is.
        `extra_answers` are combined self `self.answers.combined` when rendering
        the template.
        """
        try:
            template = self.jinja_env.from_string(value)
        except TypeError:
            # value was not a string
            return value
        try:
            return template.render({**self.answers.combined, **(extra_answers or {})})
        except UndefinedError as error:
            raise UserMessageError(str(error)) from error

    def parse_answer(self, answer: Any) -> Any:
        """Parse the answer according to the question's type."""
        ans = self.cast_answer(answer)
        choices = self._formatted_choices
        if not choices:
            return ans
        for choice in choices:
            if ans == self.cast_answer(choice.value):
                if choice.disabled:
                    raise ValueError(f"Invalid choice: {choice.disabled}")
                return ans
        raise ValueError("Invalid choice")


def parse_yaml_string(string: str) -> Any:
    """Parse a YAML string and raise a ValueError if parsing failed.

    This method is needed because :meth:`prompt` requires a ``ValueError``
    to repeat failed questions.
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


CAST_STR_TO_NATIVE: Mapping[str, Callable] = {
    "bool": cast_str_to_bool,
    "float": float,
    "int": int,
    "json": json.loads,
    "str": str,
    "yaml": parse_yaml_string,
}
