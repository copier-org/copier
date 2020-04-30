from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

# simple types
StrOrPath = Union[str, Path]
AnyByStrDict = Dict[str, Any]

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
