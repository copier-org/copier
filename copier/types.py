from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

StrOrPath = Union[str, Path]

AnyByStrDict = Dict[str, Any]

StrSeq = Sequence[str]
StrOrPathSeq = Sequence[StrOrPath]
PathSeq = Sequence[Path]
OptStrOrPathSeq = Optional[StrOrPathSeq]
OptStrSeq = Optional[StrSeq]

CheckPathFunc = Callable[[StrOrPath], bool]

T = TypeVar("T")
