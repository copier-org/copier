from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

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
OptStrOrPathSeq = Optional[StrOrPathSeq]
OptStr = Optional[str]
OptStrSeq = Optional[StrSeq]
OptAnyByStrDict = Optional[AnyByStrDict]

# miscellaneous
CheckPathFunc = Callable[[StrOrPath], bool]
T = TypeVar("T")
JSONSerializable = (dict, list, str, int, float, bool, type(None))
