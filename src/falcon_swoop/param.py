import re
from enum import Enum, unique

from typing import Any, Sequence, TypedDict
from typing_extensions import Unpack, NotRequired

from pydantic import Field


@unique
class OpParamKind(str, Enum):
    HEADER = "HEADER"
    QUERY = "QUERY"
    PATH = "PATH"


class FieldKwArgs(TypedDict):
    default: NotRequired[Any]
    alias: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    examples: NotRequired[list[Any]]
    pattern: NotRequired[str | re.Pattern[str]]
    gt: NotRequired[int | float]
    ge: NotRequired[int | float]
    lt: NotRequired[int | float]
    le: NotRequired[int | float]
    min_length: NotRequired[int]
    max_length: NotRequired[int]
    # TODO: add more?


OpParamType = type[bool | int | float | str]


class OpParam:
    def __init__(
        self,
        kind: OpParamKind,
        allow_types: Sequence[OpParamType],
        allow_optional: bool,
        field_kwargs: FieldKwArgs,
    ):
        self.field_info = Field(**field_kwargs)
        self.kind = kind
        self.allow_types = allow_types
        self.allow_optional = allow_optional


def header_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(OpParamKind.HEADER, (bool, int, float, str), True, kwargs)


def query_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(OpParamKind.QUERY, (bool, int, float, str), True, kwargs)


def path_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(OpParamKind.PATH, (int, str), False, kwargs)
