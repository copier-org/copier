from pathlib import Path
from typing import Any, Dict, Sequence, Tuple, TypeVar, Optional, Union, Callable, List

StrOrPath = Union[str, Path]
OptSeqStrOrPath = Optional[Sequence[StrOrPath]]
OptSeqStr = Optional[Sequence[str]]
AnyByStr = Dict[str, Any]
IntOrStr = Union[int, str]
CheckPathFunc = Callable[[StrOrPath], bool]
T = TypeVar("T")
