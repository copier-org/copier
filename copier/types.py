"""Complex types, annotations, validators."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    Iterator,
    Literal,
    Mapping,
    MutableMapping,
    NewType,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from pydantic import AfterValidator

if sys.version_info >= (3, 10):
    from typing import ParamSpec as ParamSpec
else:
    from typing_extensions import ParamSpec as ParamSpec

# simple types
StrOrPath = Union[str, Path]
AnyByStrDict = Dict[str, Any]
AnyByStrMutableMapping = MutableMapping[str, Any]

# sequences
IntSeq = Sequence[int]
PathSeq = Sequence[Path]

# optional types
OptBool = Optional[bool]
OptStrOrPath = Optional[StrOrPath]

# miscellaneous
T = TypeVar("T")
JSONSerializable = (dict, list, str, int, float, bool, type(None))
VCSTypes = Literal["git"]
Env = Mapping[str, str]
MissingType = NewType("MissingType", object)
MISSING = MissingType(object())
Operation = Literal["copy", "update"]


# Validators
def path_is_absolute(value: Path) -> Path:
    """Require absolute paths in an argument."""
    if not value.is_absolute():
        from .errors import PathNotAbsoluteError

        raise PathNotAbsoluteError(path=value)
    return value


def path_is_relative(value: Path) -> Path:
    """Require relative paths in an argument."""
    if value.is_absolute():
        from .errors import PathNotRelativeError

        raise PathNotRelativeError(path=value)
    return value


AbsolutePath = Annotated[Path, AfterValidator(path_is_absolute)]
RelativePath = Annotated[Path, AfterValidator(path_is_relative)]


# HACK https://github.com/copier-org/copier/pull/1880#discussion_r1887491497
class LazyDict:
    """A dict where values are functions that get evaluated only once when requested."""

    def __init__(self, **kwargs: Callable[[], Any]):
        self.pending = kwargs
        self.done: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        if key not in self.done:
            self.done[key] = self.pending[key]()
        return self.done[key]


class Phase(str, Enum):
    """The known execution phases."""

    PROMPT = "prompt"
    TASKS = "tasks"
    MIGRATE = "migrate"
    RENDER = "render"
    UNDEFINED = "undefined"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    @contextmanager
    def use(cls, phase: Phase) -> Iterator[None]:
        """Set the current phase for the duration of a context."""
        token = _phase.set(phase)
        try:
            yield
        finally:
            _phase.reset(token)

    @classmethod
    def current(cls) -> Phase:
        """Get the current phase."""
        return _phase.get()


_phase: ContextVar[Phase] = ContextVar("phase", default=Phase.UNDEFINED)
