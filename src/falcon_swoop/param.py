import re
from enum import Enum, unique

from typing import Any, Sequence, TypedDict
from typing_extensions import Unpack, NotRequired

from pydantic import Field
from pydantic.fields import FieldInfo


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
        field_kwargs: FieldKwArgs,
        kind: OpParamKind,
        allow_types: Sequence[OpParamType] = (bool, int, float, str),
        allow_optional: bool = True,
    ):
        self.field_info: FieldInfo = Field(**field_kwargs)
        self.kind = kind
        self.allow_types = allow_types
        self.allow_optional = allow_optional

    @property
    def has_default_value(self) -> bool:
        default_type = type(self.field_info.default)
        return default_type.__name__ != "PydanticUndefinedType"

    @property
    def has_none_as_default_value(self) -> bool:
        return self.field_info.default is None


def header_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(kwargs, OpParamKind.HEADER)


def query_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(kwargs, OpParamKind.QUERY)


def path_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    return OpParam(kwargs, OpParamKind.PATH, allow_types=(int, str), allow_optional=False)
