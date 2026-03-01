# ruff: noqa: D101, D102, D103, D105
import inspect
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Callable, Literal

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Self

from falcon_swoop.binary import OpAsgiBinary, OpBinary
from falcon_swoop.error import FalconSwoopConfigError
from falcon_swoop.param import OpParamType

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]  # , "OPTIONS"]
HttpMethodByFuncName: dict[str, HttpMethod] = {
    "on_get": "GET",
    "on_post": "POST",
    "on_put": "PUT",
    "on_patch": "PATCH",
    "on_delete": "DELETE",
}


OpExample = BaseModel | dict[str, Any] | str
OpType = type[BaseModel] | type[OpBinary] | type[OpAsgiBinary] | type[str] | None


@dataclass
class OpTypeDoc:
    model_type: OpType = None
    examples: dict[str, OpExample] = dataclass_field(default_factory=dict)

    @classmethod
    def with_default_example(cls, model_type: OpType = None, example: OpExample | None = None) -> Self:
        examples = {} if example is None else {"default": example}
        return cls(model_type=model_type, examples=examples)


@dataclass
class OpRequestDoc:
    by_mime: dict[str, OpTypeDoc]
    required: bool = True

    def __post_init__(self) -> None:
        if len(self.by_mime) == 0:
            raise FalconSwoopConfigError("At least one mime request type needs to be specified")


@dataclass
class OpResponseDoc:
    description: str
    by_mime: dict[str, OpTypeDoc] = dataclass_field(default_factory=dict)

    # def __post_init__(self) -> None:
    #     if len(self.by_mime) == 0:
    #         raise FalconSwoopConfigError("At least one mime response type needs to be specified")


OpResponseDocByHttpCode = dict[int, OpResponseDoc]


@dataclass
class OpFuncInput:
    name: str
    dtype: type[BaseModel] | type[OpBinary] | type[OpAsgiBinary]
    accept: list[str]
    optional: bool = False

    def __post_init__(self) -> None:
        for a in self.accept:
            if not self.ensure_content_type_format_is_ok(a):
                raise FalconSwoopConfigError(f"Configured mime type {a} for accept has invalid format")
        self.accept = [a.lower() for a in self.accept]

    def check_binary_dtype(self, operation_is_sync: bool) -> None:
        if issubclass(self.dtype, OpBinary) and not operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is async, but input type is configured as {OpBinary.__name__}, "
                f"use {OpAsgiBinary.__name__} instead"
            )
        if issubclass(self.dtype, OpAsgiBinary) and operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is sync, but input type is configured as {OpAsgiBinary.__name__}, "
                f"use {OpBinary.__name__} instead"
            )

    @classmethod
    def ensure_content_type_format_is_ok(cls, mime: str) -> bool:
        return mime.count("/") == 1 and len(mime) >= 3

    @classmethod
    def get_default_accept(cls, object_type: type[BaseModel] | type[OpBinary] | type[OpAsgiBinary]) -> str:
        if issubclass(object_type, (OpBinary, OpAsgiBinary)):
            return "application/octet-stream"
        return "application/json"

    @classmethod
    def parse_accept_config(
        cls,
        user_defined_accept: list[str] | None,
        object_type: type[BaseModel] | type[OpBinary] | type[OpAsgiBinary],
    ) -> list[str]:
        if user_defined_accept is not None and len(user_defined_accept) > 0:
            return user_defined_accept
        return [cls.get_default_accept(object_type)]

    @property
    def accepts_any(self) -> bool:
        return "*/*" in self.accept

    def can_accept(self, content_type: str | None) -> bool:
        if self.accepts_any:
            return True
        if content_type is None:
            return False
        content_type = content_type.split(sep=";", maxsplit=1)[0]
        if not self.ensure_content_type_format_is_ok(content_type):
            return False
        content_type_ = content_type.lower().strip()
        if content_type_ in self.accept:
            return True

        content_type_main = content_type_.split("/")[0]
        accepted_main_wildcards = [a.split("/")[0] for a in self.accept if a.endswith("/*")]
        return content_type_main in accepted_main_wildcards

    def to_doc(
        self,
        example: OpExample | None = None,
        examples: dict[str, OpExample] | None = None,
        examples_by_mime: dict[str, dict[str, OpExample]] | None = None,
    ) -> OpRequestDoc:
        by_mime = {}
        for mime in self.accept:
            mime_examples = {}
            if example is not None:
                mime_examples["default"] = example
            if examples is not None:
                mime_examples.update(examples)
            if examples_by_mime is not None:
                mime_examples.update(examples_by_mime.get(mime, {}))
            by_mime[mime] = OpTypeDoc(model_type=self.dtype, examples=mime_examples)
        return OpRequestDoc(by_mime=by_mime, required=not self.optional)


@dataclass
class OpFuncParam:
    name: str
    annotation: OpParamType  # TODO: remove?
    annotation_orig: Any
    info: FieldInfo
    optional: bool = False  # TODO: replace with property that interprets annotation_orig?

    @property
    def input_name(self) -> str:
        return self.info.alias or self.name

    @property
    def uses_alias(self) -> bool:
        return self.info.alias is not None


@dataclass
class OpFuncParamInput:
    model_type: type[BaseModel]
    param_by_name: dict[str, OpFuncParam]
    param_by_input_name: dict[str, OpFuncParam]
    case_sensitive: bool


@dataclass
class OpFuncOutputType:
    dtype: type[BaseModel] | type[OpBinary] | type[OpAsgiBinary]
    content_type: str

    @classmethod
    def parse_content_type_config(
        cls,
        user_defined_ct: str | None,
        object_type: type[BaseModel] | type[OpBinary] | type[OpAsgiBinary],
    ) -> str:
        if user_defined_ct is None:
            return OpFuncInput.get_default_accept(object_type)
        return user_defined_ct

    def check_binary_dtype(self, operation_is_sync: bool) -> None:
        if issubclass(self.dtype, OpBinary) and not operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is async, but return type is configured as {OpBinary.__name__}, "
                f"use {OpAsgiBinary.__name__} instead"
            )
        if issubclass(self.dtype, OpAsgiBinary) and operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is sync, but return type is configured as {OpAsgiBinary.__name__}, "
                f"use {OpBinary.__name__} instead"
            )


@dataclass
class OpFuncOutput:
    output: OpFuncOutputType | None
    hinted_wrapper: bool

    def to_doc(
        self,
        description: str,
        example: OpExample | None = None,
        examples: dict[str, OpExample] | None = None,
        # examples_by_mime: dict[str, dict[str, OpExample]] | None = None  # TODO: add later?
    ) -> OpResponseDoc:
        by_mime = {}
        if self.output is not None:
            mime_examples = {}
            if example is not None:
                mime_examples["default"] = example
            if examples is not None:
                mime_examples.update(examples)
            by_mime[self.output.content_type] = OpTypeDoc(model_type=self.output.dtype, examples=mime_examples)

        return OpResponseDoc(description=description, by_mime=by_mime)


@dataclass
class OpFuncSpec:
    func_input: OpFuncInput | None
    func_output: OpFuncOutput
    query_input: OpFuncParamInput | None
    path_input: OpFuncParamInput | None
    header_input: OpFuncParamInput | None
    context_input_name: str | None


@dataclass
class OpInfo:
    method: HttpMethod
    operation_id: str
    summary: str | None
    description: str | None
    tags: list[str]
    deprecated: bool
    request_doc: OpRequestDoc | None
    response_docs: OpResponseDocByHttpCode

    func: Callable[..., Any]

    @property
    def func_name(self) -> str:
        return self.func.__name__

    @property
    def is_sync(self) -> bool:
        return not inspect.iscoroutinefunction(self.func)


@dataclass
class OpInfoWithSpec(OpInfo):
    func_spec: OpFuncSpec
    default_status_code: int
    default_content_type: str | None
    require_valid_content_type: bool
