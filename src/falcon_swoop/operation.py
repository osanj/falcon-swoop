import inspect
import warnings
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Callable, Literal, TypedDict

from typing_extensions import NotRequired, Self, Unpack

from pydantic import create_model, BaseModel
from pydantic.fields import FieldInfo

from falcon_swoop.context import OpContext, OpAsgiContext
from falcon_swoop.error import FalconSwoopConfigError, FalconSwoopConfigWarning
from falcon_swoop.binary import BODY_TYPES, OpAsgiBinary, OpBinary
from falcon_swoop.output import OpOutput
from falcon_swoop.param import OpParam, OpParamKind, OpParamType
import falcon_swoop.type_util as type_util

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]  # , "OPTIONS"]
ATTR_OPERATION = "operation"


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
                f"Operation is async, but input type is configured as {OpBinary.__name__}, use {OpAsgiBinary.__name__} instead"
            )
        if issubclass(self.dtype, OpAsgiBinary) and operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is sync, but input type is configured as {OpAsgiBinary.__name__}, use {OpBinary.__name__} instead"
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
                f"Operation is async, but return type is configured as {OpBinary.__name__}, use {OpAsgiBinary.__name__} instead"
            )
        if issubclass(self.dtype, OpAsgiBinary) and operation_is_sync:
            raise FalconSwoopConfigError(
                f"Operation is sync, but return type is configured as {OpAsgiBinary.__name__}, use {OpBinary.__name__} instead"
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


def find_param_type(
    param: OpParam,
    annotation: Any,
    empty_val: Any,
    param_error_hint: str,
) -> tuple[OpParamType, bool]:
    optional = False
    if annotation == empty_val:
        raise FalconSwoopConfigError(
            f"{param_error_hint} requires type annotation, possible types are {param.allow_types}"
        )
    if type_util.is_union_type(annotation):
        unpacked_opt = type_util.unpack_optional_type(annotation)
        if unpacked_opt.is_optional_for_single_type:
            if param.allow_optional:
                annotation = unpacked_opt.types_without_none[0]
                optional = True
            else:
                raise FalconSwoopConfigError(f"{param_error_hint} cannot be optional")
        else:
            raise FalconSwoopConfigError(f"{param_error_hint} cannot be a union")

    unpacked_lit = type_util.unpack_literal_type(annotation)
    if unpacked_lit.is_literal:
        allowed_literal_types = (str, int, bool)
        if not unpacked_lit.has_only_values_of_type(allowed_literal_types):
            raise FalconSwoopConfigError(
                f"{param_error_hint} must only have literal values of type {allowed_literal_types}"
            )
    elif type_util.safe_issubclass(annotation, Enum):
        if not issubclass(annotation, str):
            raise FalconSwoopConfigError(
                f"{param_error_hint} must be a string enum to be usable, either subclass from str and Enum or use StrEnum"
            )
    elif annotation not in param.allow_types:
        raise FalconSwoopConfigError(
            f"{param_error_hint} has unsupported type annotation {annotation}, possible types are {param.allow_types}"
        )
    return annotation, optional


def find_params(
    signature: inspect.Signature,
    param_names: set[str],
    kind: OpParamKind,
    operation_id: str,
    case_sensitive: bool = True,
) -> tuple[OpFuncParamInput | None, set[str]]:
    param_inputs = []

    for param_name in param_names:
        input_argument = signature.parameters[param_name]
        if input_argument.default is None or input_argument.default == signature.empty:
            continue
        if not isinstance(input_argument.default, OpParam):
            continue
        param: OpParam = input_argument.default
        if param.kind != kind:
            continue
        param_kind_str = param.kind.capitalize()
        error_start = f"{param_kind_str} parameter {input_argument.name}"
        annotation, optional = find_param_type(
            param=param,
            annotation=input_argument.annotation,
            empty_val=signature.empty,
            param_error_hint=error_start,
        )
        if optional and param.has_default_value and not param.has_none_as_default_value:
            warnings.warn(
                f"{error_start} is type hinted as optional, but will never be None because of default value",
                FalconSwoopConfigWarning,
            )
        param_input = OpFuncParam(
            name=param_name,
            annotation=annotation,
            annotation_orig=input_argument.annotation,
            info=param.field_info,
            optional=optional,
        )
        if not case_sensitive:
            input_name = param_input.input_name
            if not (input_name.islower() or input_name.isupper()):
                alias_hint = " (see alias)" if param_input.uses_alias else ""
                warnings.warn(
                    f"{error_start} has mixed case{alias_hint}, but {param_kind_str} parameters are "
                    "case insensitive, it's recommend to use either lowercase or uppercase only",
                    FalconSwoopConfigWarning,
                )
        param_inputs.append(param_input)

    if len(param_inputs) == 0:
        return None, set()

    used_param_names = {pi.name for pi in param_inputs}
    param_model_name = f"{operation_id}{kind.lower().capitalize()}Params"
    param_type = create_model(param_model_name, **{pi.name: (pi.annotation_orig, pi.info) for pi in param_inputs})  # type: ignore[call-overload]
    func_input = OpFuncParamInput(
        model_type=param_type,
        param_by_name={pi.name: pi for pi in param_inputs},
        param_by_input_name={pi.input_name: pi for pi in param_inputs},
        case_sensitive=case_sensitive,
    )
    return func_input, used_param_names


def find_context_input(
    signature: inspect.Signature,
    param_names: set[str],
    is_sync: bool,
) -> str | None:
    expected_type = OpContext if is_sync else OpAsgiContext
    incorrect_type = OpAsgiContext if is_sync else OpContext

    context_param_name: str | None = None
    for param_name in param_names:
        input_argument = signature.parameters[param_name]
        input_type = input_argument.annotation

        if input_type == incorrect_type:
            operation_kind = "synchronous" if is_sync else "asynchronous"
            raise FalconSwoopConfigError(
                f"Argument {param_name} has type {input_type}, but expected {expected_type} "
                f"since the operation is {operation_kind}"
            )

        if input_type == expected_type:
            if context_param_name is not None:
                raise FalconSwoopConfigError(
                    f"Duplicated context parameter, {context_param_name} already receives the operation context, "
                    f"{param_name} should be removed"
                )
            context_param_name = param_name

    return context_param_name


class OperationKwArgs(TypedDict):
    operation_id: NotRequired[str]
    summary: NotRequired[str]
    description: NotRequired[str]
    tags: NotRequired[list[str]]
    accept: NotRequired[str | list[str]]
    require_valid_content_type: NotRequired[bool]
    deprecated: NotRequired[bool]
    default_status: NotRequired[int | tuple[int, str]]
    request_example: NotRequired[OpExample]
    request_examples: NotRequired[dict[str, OpExample]]
    request_examples_by_mime: NotRequired[dict[str, dict[str, OpExample]]]
    response_content_type: NotRequired[str]  # TODO: allow also list like for accept?
    response_example: NotRequired[OpExample]
    response_examples: NotRequired[dict[str, OpExample]]
    more_response_docs: NotRequired[OpResponseDocByHttpCode]


def get_operation_id_or_default(operation_id: str | None, func: Callable[..., Any]) -> str:
    if operation_id is not None:
        return operation_id
    func_name_parts = func.__name__.split("_")
    return "".join([func_name_parts[0]] + [p.capitalize() for p in func_name_parts[1:]])


def inspect_function(
    func: Callable[..., Any],
    op_id: str,
    accept: str | list[str] | None,
    response_ct: str | None,
) -> OpFuncSpec:
    signature = inspect.signature(func)
    is_sync = not inspect.iscoroutinefunction(func)

    # --- http request params of various sort
    input_params = signature.parameters.keys() - {"self"}

    header_input, header_params = find_params(signature, input_params, OpParamKind.HEADER, op_id, case_sensitive=False)
    query_input, query_params = find_params(signature, input_params, OpParamKind.QUERY, op_id)
    path_input, path_params = find_params(signature, input_params, OpParamKind.PATH, op_id)
    input_params.difference_update(header_params | query_params | path_params)

    context_input_name = find_context_input(signature, input_params, is_sync=is_sync)
    if context_input_name is not None:
        input_params.discard(context_input_name)

    # --- http request body
    op_input = None
    if len(input_params) == 1:
        param = signature.parameters[input_params.pop()]
        param_annotation = param.annotation
        param_type = param.annotation
        optional = False

        if type_util.is_union_type(param_annotation):
            unpacked = type_util.unpack_optional_type(param_annotation)
            if unpacked.is_optional_for_single_type:
                param_type = unpacked.types_without_none[0]
                optional = True
            else:
                raise FalconSwoopConfigError(f"Operation input parameter {param.name} cannot be a union")

        if not type_util.safe_issubclass(param_type, BODY_TYPES):
            raise FalconSwoopConfigError(
                f"Operation input parameter {param.name} needs to be one of {BODY_TYPES}, bot got {param_type}"
            )
        if isinstance(accept, str):
            accept = [accept]
        op_input = OpFuncInput(
            name=param.name,
            dtype=param_type,
            optional=optional,
            accept=OpFuncInput.parse_accept_config(accept, param_type),
        )
        op_input.check_binary_dtype(is_sync)

    elif len(input_params) > 1:
        raise FalconSwoopConfigError(f"More than 1 parameter found that could be http body: {','.join(input_params)}")

    # --- http response body
    output_candidate = signature.return_annotation
    hinted_wrapper = False
    if output_candidate == signature.empty:
        output_candidate = None

    if type_util.is_generic_type(output_candidate, OpOutput):
        output_candidate = type_util.unpack_generic_type(output_candidate, none_type_to_none=True)[0]
        hinted_wrapper = True
    elif type_util.safe_issubclass(output_candidate, OpOutput):
        raise FalconSwoopConfigError(
            f"The payload type for {OpOutput.__name__} is missing, "
            f"the type hint should be {OpOutput.__name__}[<return_type>]"
        )

    output_type = None
    if output_candidate is not None:
        if type_util.is_union_type(output_candidate):
            raise FalconSwoopConfigError("Return type cannot be a union or optional")
        if not type_util.safe_issubclass(output_candidate, BODY_TYPES):
            raise FalconSwoopConfigError(f"Return type needs to be one of {BODY_TYPES}, bot got {output_candidate}")
        output_type = OpFuncOutputType(
            dtype=output_candidate,
            content_type=OpFuncOutputType.parse_content_type_config(response_ct, output_candidate),
        )
        output_type.check_binary_dtype(is_sync)
    op_output = OpFuncOutput(
        output=output_type,
        hinted_wrapper=hinted_wrapper,
    )

    return OpFuncSpec(
        func_input=op_input,
        func_output=op_output,
        query_input=query_input,
        path_input=path_input,
        header_input=header_input,
        context_input_name=context_input_name,
    )


def inspect_operation(
    method: HttpMethod,
    func: Callable[..., Any],
    **kwargs: Unpack[OperationKwArgs],
) -> OpInfoWithSpec:
    op_id = get_operation_id_or_default(kwargs.get("operation_id"), func)
    response_ct = kwargs.get("response_content_type")

    func_spec = inspect_function(
        func,
        op_id=op_id,
        accept=kwargs.get("accept"),
        response_ct=response_ct,
    )
    op_input = func_spec.func_input

    request_doc: OpRequestDoc | None = None
    if op_input is not None:
        request_doc = op_input.to_doc(
            example=kwargs.get("request_example"),
            examples=kwargs.get("request_examples"),
            examples_by_mime=kwargs.get("request_examples_by_mime"),
        )

    resp_status: int = 200
    resp_desc: str = "ok"
    match kwargs.get("default_status", (resp_status, resp_desc)):
        case int(status):
            resp_status = status
        case (int(status), str(desc)):
            resp_status = status
            resp_desc = desc
        case _:
            raise ValueError("Could not match default status input")
    response_doc = func_spec.func_output.to_doc(description=resp_desc)
    response_docs = {resp_status: response_doc}
    more_response_docs = kwargs.get("more_response_docs", {})
    if resp_status in more_response_docs:
        raise FalconSwoopConfigError(
            f"Response docs for default HTTP status code {resp_status} are generated, cannot be provided"
        )
    response_docs.update(more_response_docs)

    return OpInfoWithSpec(
        method=method,
        operation_id=op_id,
        summary=kwargs.get("summary"),
        description=kwargs.get("description"),
        tags=kwargs.get("tags", []),
        deprecated=kwargs.get("deprecated", False),
        request_doc=request_doc,
        response_docs=response_docs,
        func=func,
        # ---
        func_spec=func_spec,
        default_status_code=resp_status,
        default_content_type=response_ct,
        require_valid_content_type=kwargs.get("require_valid_content_type", True),
    )


def operation(method: HttpMethod, **kwargs: Unpack[OperationKwArgs]) -> Callable[..., Any]:
    """
    Decorator for API operations.
    :param method: HTTP method required in request
    :param operation_id: specific openAPI operation id, if not provided the camelCased function name will be used
    :param deprecated: flag to mark the operation as deprecated in the openapi docs (default: False)
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation(method, func, **kwargs)
        setattr(func, ATTR_OPERATION, info)
        return func

    return wrap


class OperationDocKwArgs(TypedDict):
    operation_id: NotRequired[str]
    summary: NotRequired[str]
    description: NotRequired[str]
    tags: NotRequired[list[str]]
    deprecated: NotRequired[bool]
    request_doc: NotRequired[OpRequestDoc]
    response_docs: NotRequired[OpResponseDocByHttpCode]


def inspect_operation_doc(
    func: Callable[..., Any],
    **kwargs: Unpack[OperationDocKwArgs],
) -> OpInfo:
    operation_id = get_operation_id_or_default(kwargs.get("operation_id"), func)
    func_name_method_mapping: dict[str, HttpMethod] = {
        "on_get": "GET",
        "on_post": "POST",
        "on_put": "PUT",
        "on_patch": "PATCH",
        "on_delete": "DELETE",
    }

    method = func_name_method_mapping.get(func.__name__)
    if method is None:
        raise FalconSwoopConfigError(
            f"The annotated method needs to have one of "
            f"the falcon request methods: {', '.join(func_name_method_mapping.keys())}"
        )

    return OpInfo(
        method=method,
        operation_id=operation_id,
        summary=kwargs.get("summary"),
        description=kwargs.get("description"),
        tags=kwargs.get("tags", []),
        deprecated=kwargs.get("deprecated", False),
        request_doc=kwargs.get("request_doc"),
        response_docs=kwargs.get("response_docs", {}),
        func=func,
    )


def operation_doc(**kwargs: Unpack[OperationDocKwArgs]) -> Callable[..., Any]:
    """
    ...
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation_doc(func, **kwargs)
        setattr(func, ATTR_OPERATION, info)
        return func

    return wrap
