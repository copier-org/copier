"""Complex types, annotations, validators."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Sequence, TypeVar, Union

from pydantic.validators import path_validator

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator


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

# miscellaneous
T = TypeVar("T")
JSONSerializable = (dict, list, str, int, float, bool, type(None))
VCSTypes = Literal["git"]
Env = Mapping[str, str]


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
if TYPE_CHECKING:
    AbsolutePath = Path
    RelativePath = Path
else:

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
