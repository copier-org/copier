from pathlib import Path
from typing import Any, Dict, Optional, Sequence, TypeVar, Union

IntOrStr = Union[int, str]
StrOrPath = Union[str, Path]

AnyByStrDict = Dict[str, Any]

OptStrOrPathSeq = Optional[Sequence[StrOrPath]]
OptStrSeq = Optional[Sequence[str]]

T = TypeVar("T")
