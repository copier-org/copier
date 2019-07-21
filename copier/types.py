from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

StrOrPath = Union[str, Path]

AnyByStrDict = Dict[str, Any]

IntSeq = Sequence[int]
StrSeq = Sequence[str]
StrOrPathSeq = Sequence[StrOrPath]
PathSeq = Sequence[Path]

OptBool = Optional[bool]
OptStrOrPathSeq = Optional[StrOrPathSeq]
OptStrSeq = Optional[StrSeq]

CheckPathFunc = Callable[[StrOrPath], bool]

T = TypeVar("T")
