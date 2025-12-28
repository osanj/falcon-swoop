import inspect
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Callable, Literal, NotRequired, TypedDict
from typing_extensions import Self, Unpack

from pydantic import create_model, BaseModel
from pydantic.fields import FieldInfo

from falcon_swoop.error import FalconSwoopConfigError
from falcon_swoop.param import Param, ParamKind


HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]  # , "OPTIONS"]
MimeType = Literal["application/json"]
ATTR_OPERATION = "operation"


@dataclass
class OpApiModelInput:
    name: str
    model_type: type[BaseModel]
    optional: bool = False


@dataclass
class OpApiParamInput:
    name: str
    annotation: type[bool | int | float | str]
    info: FieldInfo
    optional: bool = False


OpExample = BaseModel | dict[str, Any] | str
OpType = type[BaseModel] | type[str] | None


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
class OpFuncSpec:
    func_input: OpApiModelInput | None
    query_input: type[BaseModel] | None
    path_input: type[BaseModel] | None
    header_input: type[BaseModel] | None
    # allow raw input?
    # accept mime type?
    func_output_model: type[BaseModel] | None


@dataclass
class OpInfo:
    method: HttpMethod
    operation_id: str
    tags: list[str]
    deprecated: bool
    request_doc: OpRequestDoc | None
    response_docs: OpResponseDocByHttpCode
    # accept: list[MimeType]
    # http_status_code: int
    # http_description: str

    func: Callable[..., Any]

    @property
    def func_name(self) -> str:
        return self.func.__name__


@dataclass
class OpInfoWithSpec(OpInfo):
    func_spec: OpFuncSpec


def find_params(
    signature: inspect.Signature, param_names: set[str], kind: ParamKind, operation_id: str
) -> tuple[type[BaseModel] | None, set[str]]:
    param_inputs = []

    for param_name in param_names:
        param = signature.parameters[param_name]
        if param.default is None or param.default == signature.empty:
            continue
        if not isinstance(param.default, Param):
            continue
        default: Param = param.default
        if default.kind != kind:
            continue
        if param.annotation is None:
            raise FalconSwoopConfigError(
                f"{default.kind.capitalize()} parameter {param.name} requires type annotation, "
                f"possible types are {default.allowed_types}"
            )
        if param.annotation not in default.allowed_types:
            raise FalconSwoopConfigError(
                f"{default.kind.capitalize()} parameter {param.name} has unsupported type "
                f"annotation {param.annotation}, possible types are {default.allowed_types}"
            )
        param_input = OpApiParamInput(
            name=param_name,
            annotation=param.annotation,
            info=default.field_info,
        )
        param_inputs.append(param_input)

    if len(param_inputs) == 0:
        return None, set()

    # TODO: add warning for header parameters that seem to imply case sensitivity
    used_param_names = {pi.name for pi in param_inputs}
    param_model_name = f"{operation_id}{kind.lower().capitalize()}Params"
    param_type = create_model(
        param_model_name, **{pi.name: (pi.annotation, pi.info) for pi in param_inputs}
    )  # type: ignore[call-overload]
    return param_type, used_param_names


class OperationKwArgs(TypedDict):
    operation_id: NotRequired[str]
    tags: NotRequired[list[str]]
    accept: NotRequired[list[MimeType]]
    deprecated: NotRequired[bool]
    default_status: NotRequired[int | tuple[int, str]]
    default_request_example: NotRequired[OpExample]
    default_response_example: NotRequired[OpExample]
    more_response_docs: NotRequired[OpResponseDocByHttpCode]


def get_operation_id_or_default(operation_id: str | None, func: Callable[..., Any]) -> str:
    if operation_id is not None:
        return operation_id
    func_name_parts = func.__name__.split("_")
    return "".join([func_name_parts[0]] + [p.capitalize() for p in func_name_parts[1:]])


def inspect_operation(
    method: HttpMethod,
    func: Callable[..., Any],
    **kwargs: Unpack[OperationKwArgs],
) -> OpInfoWithSpec:
    signature = inspect.signature(func)
    op_input = None
    op_output_type = None
    operation_id = get_operation_id_or_default(kwargs.get("operation_id"), func)

    input_params = signature.parameters.keys() - {"self"}

    header_input, header_params = find_params(signature, input_params, ParamKind.HEADER, operation_id)
    query_input, query_params = find_params(signature, input_params, ParamKind.QUERY, operation_id)
    path_input, path_params = find_params(signature, input_params, ParamKind.PATH, operation_id)

    input_params.difference_update(header_params | query_params | path_params)

    if len(input_params) == 1:
        param = signature.parameters[input_params.pop()]
        param_type = param.annotation
        if not issubclass(param_type, BaseModel):
            raise FalconSwoopConfigError(
                f"Parameter type of {param.name} needs to be a subclass of {BaseModel.__name__}"
            )
        op_input = OpApiModelInput(param.name, param_type)
    elif len(input_params) > 1:
        raise FalconSwoopConfigError("More than 1 parameter found")

    if signature.return_annotation not in (signature.empty, None):
        if not issubclass(signature.return_annotation, BaseModel):
            raise FalconSwoopConfigError(f"Return type needs to be a subclass of {BaseModel.__name__}")
        op_output_type = signature.return_annotation

    # default_accept: list[MimeType] = ["application/json"]
    # accept=kwargs.get("accept", default_accept),
    request_doc: OpRequestDoc | None = None
    if op_input is not None:
        request_doc = OpRequestDoc(
            required=not op_input.optional,
            by_mime={
                "application/json": OpTypeDoc.with_default_example(
                    model_type=op_input.model_type,
                    example=kwargs.get("default_request_example"),
                )
            },
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
    response_type_by_mime = {}
    if op_output_type is not None:
        response_type_by_mime["application/json"] = OpTypeDoc.with_default_example(
            model_type=op_output_type,
            example=kwargs.get("default_response_example"),
        )
    response_docs = {resp_status: OpResponseDoc(description=resp_desc, by_mime=response_type_by_mime)}
    more_response_docs = kwargs.get("more_response_docs", {})
    if resp_status in more_response_docs:
        raise FalconSwoopConfigError(
            f"Response docs for default HTTP status code {resp_status} are generated, cannot be provided"
        )
    response_docs.update(more_response_docs)

    return OpInfoWithSpec(
        method=method,
        operation_id=operation_id,
        tags=kwargs.get("tags", []),
        deprecated=kwargs.get("deprecated", False),
        request_doc=request_doc,
        response_docs=response_docs,
        func=func,
        func_spec=OpFuncSpec(
            func_input=op_input,
            func_output_model=op_output_type,
            query_input=query_input,
            path_input=path_input,
            header_input=header_input,
        ),
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
    tags: NotRequired[list[str]]
    accept: NotRequired[list[MimeType]]
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
