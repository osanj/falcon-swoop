from typing import Literal, ParamSpec

from pydantic import Field
from pydantic.fields import FieldInfo


class Param:
    def __init__(self, field_info: FieldInfo, param_type: Literal["header", "query", "path"]):
        self.field_info = field_info
        self.type = param_type


P = ParamSpec("P")

def ApiHeaderParam(*args: P.args, **kwargs: P.kwargs) -> Param:
    field_info = Field(*args, **kwargs)
    return Param(field_info, "header")

def ApiQueryParam(*args: P.args, **kwargs: P.kwargs) -> Param:
    field_info = Field(*args, **kwargs)
    return Param(field_info, "query")

def ApiPathParam(*args: P.args, **kwargs: P.kwargs) -> Param:
    field_info = Field(*args, **kwargs)
    return Param(field_info, "path")
