import re
from enum import Enum, unique

from typing import Any, Sequence, TypedDict
from typing_extensions import Unpack, NotRequired

from pydantic import Field


@unique
class ParamKind(str, Enum):
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


class Param:
    def __init__(
        self,
        kind: ParamKind,
        allowed_types: Sequence[type[bool | int | float | str]],
        field_kwargs: FieldKwArgs,
    ):
        self.field_info = Field(**field_kwargs)
        self.kind = kind
        self.allowed_types = allowed_types


def header_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return Param(ParamKind.HEADER, (bool, int, float, str), kwargs)


def query_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return Param(ParamKind.QUERY, (bool, int, float, str), kwargs)


def path_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return Param(ParamKind.PATH, (int, str), kwargs)
