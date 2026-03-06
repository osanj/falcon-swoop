import re
from enum import Enum, unique
from typing import Any, Sequence, TypedDict

from pydantic import Field
from pydantic.fields import FieldInfo
from typing_extensions import NotRequired, Unpack


@unique
class OpParamKind(str, Enum):  # noqa: D101
    HEADER = "HEADER"
    QUERY = "QUERY"
    PATH = "PATH"


class FieldKwArgs(TypedDict):  # noqa: D101
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
    deprecated: NotRequired[bool]  # only pydantic >=2.7
    # TODO: add more?


OpParamType = type[bool | int | float | str]


class OpParam:  # noqa: D101
    def __init__(  # noqa: D107
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
    def has_default_value(self) -> bool:  # noqa: D102
        default_type = type(self.field_info.default)
        return default_type.__name__ != "PydanticUndefinedType"

    @property
    def has_none_as_default_value(self) -> bool:  # noqa: D102
        return self.field_info.default is None


def header_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    """Create a header parameter, the input to this function will be used for ``pydantic.Field(**kwargs)``."""
    return OpParam(kwargs, OpParamKind.HEADER)


def query_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    """Create a query parameter, the input to this function will be used for ``pydantic.Field(**kwargs)``."""
    return OpParam(kwargs, OpParamKind.QUERY)


def path_param(**kwargs: Unpack[FieldKwArgs]) -> Any:
    """Create a path parameter, the input to this function will be used for ``pydantic.Field(**kwargs)``.

    Note that only string and integer types are supported for path parameters.
    Also, path parameters must not be optional.
    """
    return OpParam(kwargs, OpParamKind.PATH, allow_types=(int, str), allow_optional=False)
