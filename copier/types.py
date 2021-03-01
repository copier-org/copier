"""Complex types, annotations, validators."""

from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from pydantic.validators import path_validator

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator


# simple types
StrOrPath = Union[str, Path]
AnyByStrDict = Dict[str, Any]
AnyByStrDictOrTuple = Union[AnyByStrDict, Tuple[str, Any]]

# sequences
IntSeq = Sequence[int]
StrSeq = Sequence[str]
StrOrPathSeq = Sequence[StrOrPath]
PathSeq = Sequence[Path]

# optional types
OptBool = Optional[bool]
OptStrOrPath = Optional[StrOrPath]
OptStrOrPathSeq = Optional[StrOrPathSeq]
OptStr = Optional[str]
OptStrSeq = Optional[StrSeq]
OptAnyByStrDict = Optional[AnyByStrDict]

# miscellaneous
CheckPathFunc = Callable[[StrOrPath], bool]
Choices = Union[List[Any], Dict[Any, Any]]
T = TypeVar("T")
JSONSerializable = (dict, list, str, int, float, bool, type(None))
Filters = Dict[str, Callable]
LoaderPaths = Union[str, Iterable[str]]
VCSTypes = Literal["git"]
ExcInfo = Tuple[BaseException, Exception, TracebackType]


class AllowArbitraryTypes:
    arbitrary_types_allowed = True


# Validators
def path_is_absolute(value: Path) -> Path:
    if not value.is_absolute():
        from .errors import PathNotAbsoluteError

        raise PathNotAbsoluteError(path=value)
    return value


def path_is_relative(value: Path) -> Path:
    if value.is_absolute():
        from .errors import PathNotRelativeError

        raise PathNotRelativeError(path=value)
    return value


# Validated types
class AbsolutePath(Path):
    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield path_validator
        yield path_is_absolute


class RelativePath(Path):
    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield path_validator
        yield path_is_relative
