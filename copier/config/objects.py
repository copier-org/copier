"""Pydantic models, exceptions and default values."""
import datetime
import json
from collections import ChainMap
from contextlib import suppress
from copy import deepcopy
from hashlib import sha512
from os import urandom
from pathlib import Path
from typing import (
    Any,
    Callable,
    ChainMap as t_ChainMap,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from jinja2 import UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.validation import Validator
from pydantic import BaseModel, Extra, Field, StrictBool, validator
from pygments.lexers.data import JsonLexer, YamlLexer
from PyInquirer.prompt import prompt

from ..tools import cast_answer_type, cast_str_to_bool, force_str_end, parse_yaml_string
from ..types import AnyByStrDict, OptStr, PathSeq, StrOrPathSeq, StrSeq

# Default list of files in the template to exclude from the rendered project
DEFAULT_EXCLUDE: Tuple[str, ...] = (
    "copier.yaml",
    "copier.yml",
    "~*",
    "*.py[co]",
    "__pycache__",
    ".git",
    ".DS_Store",
    ".svn",
)

DEFAULT_DATA: AnyByStrDict = {
    "now": datetime.datetime.utcnow,
    "make_secret": lambda: sha512(urandom(48)).hexdigest(),
}

DEFAULT_TEMPLATES_SUFFIX = ".tmpl"

CAST_STR_TO_NATIVE: Dict[str, Callable] = {
    "bool": cast_str_to_bool,
    "float": float,
    "int": int,
    "json": json.loads,
    "str": str,
    "yaml": parse_yaml_string,
}


class UserMessageError(Exception):
    """Exit the program giving a message to the user."""


class NoSrcPathError(UserMessageError):
    pass


class InvalidTypeError(TypeError):
    pass


class EnvOps(BaseModel):
    """Jinja2 environment options."""

    autoescape: StrictBool = False
    block_start_string: str = "[%"
    block_end_string: str = "%]"
    comment_start_string: str = "[#"
    comment_end_string: str = "#]"
    variable_start_string: str = "[["
    variable_end_string: str = "]]"
    keep_trailing_newline: StrictBool = True

    class Config:
        allow_mutation = False
        extra = Extra.allow


class Migrations(BaseModel):
    version: str
    before: Sequence[Union[str, StrSeq]] = ()
    after: Sequence[Union[str, StrSeq]] = ()


class ConfigData(BaseModel):
    """A model holding configuration data."""

    src_path: Path
    subdirectory: OptStr
    dst_path: Path
    extra_paths: PathSeq = ()
    exclude: StrOrPathSeq = DEFAULT_EXCLUDE
    skip_if_exists: StrOrPathSeq = ()
    tasks: Sequence[Union[str, StrSeq]] = ()
    envops: EnvOps = EnvOps()
    templates_suffix: str = DEFAULT_TEMPLATES_SUFFIX
    original_src_path: OptStr
    commit: OptStr
    old_commit: OptStr
    cleanup_on_error: StrictBool = True
    force: StrictBool = False
    only_diff: StrictBool = True
    pretend: StrictBool = False
    quiet: StrictBool = False
    skip: StrictBool = False
    use_prereleases: StrictBool = False
    vcs_ref: OptStr
    migrations: Sequence[Migrations] = ()
    secret_questions: StrSeq = ()
    answers_file: Path = Path(".copier-answers.yml")
    data_from_init: AnyByStrDict = {}
    data_from_asking_user: AnyByStrDict = {}
    data_from_answers_file: AnyByStrDict = {}
    data_from_template_defaults: AnyByStrDict = {}

    # Private
    _data_mutable: AnyByStrDict

    def __init__(self, **kwargs: AnyByStrDict):
        super().__init__(**kwargs)
        self.data_from_template_defaults.setdefault("_folder_name", self.dst_path.name)
        # HACK https://github.com/samuelcolvin/pydantic/issues/655#issuecomment-570310120
        object.__setattr__(self, "_data_mutable", {})

    @validator("skip", always=True)
    def mutually_exclusive_flags(cls, v, values):  # noqa: B902
        if v and values["force"]:
            raise ValueError("Flags `force` and `skip` are mutually exclusive.")
        return v

    # sanitizers
    @validator("src_path", "dst_path", "extra_paths", pre=True, each_item=True)
    def resolve_path(cls, v: Path) -> Path:  # noqa: B902
        return Path(v).expanduser().resolve()

    @validator("src_path", "extra_paths", pre=True, each_item=True)
    def dir_must_exist(cls, v: Path) -> Path:  # noqa: B902
        if not v.exists():
            raise ValueError("Project template not found.")
        if not v.is_dir():
            raise ValueError("Project template not a folder.")
        return v

    @validator(
        "data_from_init",
        "data_from_asking_user",
        "data_from_answers_file",
        "data_from_template_defaults",
        pre=True,
        each_item=True,
    )
    def dict_copy(cls, v: AnyByStrDict) -> AnyByStrDict:
        """Make sure all dicts are copied."""
        return deepcopy(v)

    @property
    def data(self) -> t_ChainMap[str, Any]:
        """The data object comes from different sources, sorted by priority."""
        return ChainMap(
            self._data_mutable,
            self.data_from_asking_user,
            self.data_from_init,
            self.data_from_answers_file,
            self.data_from_template_defaults,
            DEFAULT_DATA,
        )

    # configuration
    class Config:
        allow_mutation = False
        anystr_strip_whitespace = True


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

    def get_default(self, inquirer_cast: bool) -> Any:
        cast_fn = self.get_cast_fn()
        try:
            result = self.questionary.answers_forced[self.var_name]
        except KeyError:
            try:
                result = self.questionary.answers_last[self.var_name]
            except KeyError:
                result = self.render_value(self.default)
                result = cast_answer_type(result, cast_fn)
        if not inquirer_cast or self.type_name == "bool":
            if isinstance(result, str):
                result = cast_fn(result)
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
        if answer == self.get_default(inquirer_cast=True):
            return self.get_default(inquirer_cast=False)
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
            "default": self.get_default(inquirer_cast=True),
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
                new_answer = question.get_default(inquirer_cast=False)
                cast_fn = question.get_cast_fn()
                casted_previous_answer = cast_answer_type(
                    previous_answers.get(question.var_name), cast_fn
                )
                if new_answer != casted_previous_answer:
                    self.answers_user[question.var_name] = new_answer
        return self.answers_user


Question.update_forward_refs()
