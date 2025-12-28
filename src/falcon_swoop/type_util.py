from dataclasses import dataclass
from typing import Any, Union, get_args
import types


def is_union_type(hint: Any) -> bool:
    return type(hint) in (Union, types.UnionType)


@dataclass
class UnpackedOptionalType:
    is_optional: bool
    types_without_none: list[type[Any]]

    @property
    def is_optional_for_single_type(self) -> bool:
        return self.is_optional and len(self.types_without_none) == 1


def unpack_optional_type(hint: Any) -> UnpackedOptionalType:
    if not is_union_type(hint):
        return UnpackedOptionalType(False, [])
    args = get_args(hint)
    return UnpackedOptionalType(
        is_optional=types.NoneType in args,
        types_without_none=[arg for arg in args if arg is not types.NoneType],
    )
