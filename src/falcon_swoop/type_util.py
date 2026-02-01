from dataclasses import dataclass
from typing import Any, Literal, Sequence, Union, get_args, get_origin
import types


def safe_issubclass(x: Any, a_tuple: type[Any] | tuple[type[Any], ...]) -> bool:
    try:
        return issubclass(x, a_tuple)
    except TypeError:
        return False


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


def is_literal_type(hint: Any) -> bool:
    return get_origin(hint) is Literal


@dataclass
class UnpackedLiteralType:
    is_literal: bool
    literal_values: list[Any]

    def has_only_values_of_type(self, allowed_types: Sequence[type[Any]]) -> bool:
        for lv in self.literal_values:
            if type(lv) not in allowed_types:
                return False
        return True


def unpack_literal_type(hint: Any) -> UnpackedLiteralType:
    if not is_literal_type(hint):
        return UnpackedLiteralType(False, [])
    return UnpackedLiteralType(
        is_literal=True,
        literal_values=list(get_args(hint)),
    )


def is_generic_type(hint: Any, exp_type: type[Any]) -> bool:
    return get_origin(hint) is exp_type


def unpack_generic_type(hint: Any) -> list[Any]:
    return list(get_args(hint))
