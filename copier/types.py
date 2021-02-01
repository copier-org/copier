"""All complex types and annotations are declared here."""

from pathlib import Path
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

from copier.validators import path_is_absolute, path_is_relative

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
