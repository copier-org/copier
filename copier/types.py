from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

StrOrPath = Union[str, Path]

AnyByStrDict = Dict[str, Any]

OptStrOrPathSeq = Optional[Sequence[StrOrPath]]
OptStrSeq = Optional[Sequence[str]]

CheckPathFunc = Callable[[StrOrPath], bool]

T = TypeVar("T")
