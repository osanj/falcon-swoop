import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal, NotRequired, Sequence, TypedDict
from typing_extensions import Unpack

from pydantic import create_model, BaseModel
from pydantic.fields import FieldInfo

from falcon_api.error import FalconApiConfigError
from falcon_api.param import Param, ParamKind


HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]  # , "OPTIONS"]
MimeType = Literal["application/json"]
ATTR_OPERATION = "operation"


@dataclass
class OperationApiModelInput:
    name: str
    model: type[BaseModel]


@dataclass
class OperationApiParamInput:
    name: str
    annotation: type[bool | int | float | str]
    info: FieldInfo


@dataclass
class OperationDocs:
    pass


@dataclass
class OperationInfo:
    method: HttpMethod
    operation_id: str
    tags: list[str]
    accept: list[MimeType]
    deprecated: bool

    func: Callable[..., Any]
    func_input: OperationApiModelInput | None
    query_input: type[BaseModel] | None
    path_input: type[BaseModel] | None
    header_input: type[BaseModel] | None
    # allow raw input?
    # accept mime type?
    func_output_model: type[BaseModel] | None

    docs: OperationDocs | None

    @property
    def func_name(self) -> str:
        return self.func.__name__


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
            raise FalconApiConfigError(
                f"{default.kind.capitalize()} parameter {param.name} requires type annotation, "
                f"possible types are {default.allowed_types}"
            )
        if param.annotation not in default.allowed_types:
            raise FalconApiConfigError(
                f"{default.kind.capitalize()} parameter {param.name} has unsupported type "
                f"annotation {param.annotation}, possible types are {default.allowed_types}"
            )
        param_input = OperationApiParamInput(
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
    operation_id: NotRequired[str | None]
    tags: NotRequired[list[str]]
    accept: NotRequired[list[MimeType]]
    docs: NotRequired[OperationDocs | None]
    deprecated: NotRequired[bool]


def inspect_operation(method: HttpMethod, func: Callable[..., Any], **kwargs: Unpack[OperationKwArgs]) -> OperationInfo:
    signature = inspect.signature(func)
    op_input = None
    t_output = None

    operation_id = kwargs.get("operation_id")
    if operation_id is None:
        func_name_parts = func.__name__.split("_")
        operation_id = "".join([func_name_parts[0]] + [p.capitalize() for p in func_name_parts[1:]])

    input_params = signature.parameters.keys() - {"self"}

    header_input, header_params = find_params(signature, input_params, ParamKind.HEADER, operation_id)
    query_input, query_params = find_params(signature, input_params, ParamKind.QUERY, operation_id)
    path_input, path_params = find_params(signature, input_params, ParamKind.PATH, operation_id)

    input_params.difference_update(header_params | query_params | path_params)

    if len(input_params) == 1:
        param = signature.parameters[input_params.pop()]
        param_type = param.annotation
        if not issubclass(param_type, BaseModel):
            raise FalconApiConfigError(f"Parameter type of {param.name} needs to be a subclass of {BaseModel.__name__}")
        op_input = OperationApiModelInput(param.name, param_type)
    elif len(input_params) > 1:
        raise FalconApiConfigError("More than 1 parameter found")

    if signature.return_annotation != signature.empty:
        if not issubclass(signature.return_annotation, BaseModel):
            raise FalconApiConfigError(f"Return type needs to be a subclass of {BaseModel.__name__}")
        t_output = signature.return_annotation

    default_accept: list[MimeType] = ["application/json"]
    return OperationInfo(
        method=method,
        operation_id=operation_id,
        tags=kwargs.get("tags", []),
        accept=kwargs.get("accept", default_accept),
        deprecated=kwargs.get("deprecated", False),
        func=func,
        func_input=op_input,
        func_output_model=t_output,
        query_input=query_input,
        path_input=path_input,
        header_input=header_input,
        docs=kwargs.get("docs"),
    )


def inspect_operation_doc(
    func: Callable[..., Any],
) -> OperationDocs:
    func_name_method_mapping: dict[str, HttpMethod] = {
        "on_get": "GET",
        "on_post": "POST",
    }

    method = func_name_method_mapping.get(func.__name__)
    if method is None:
        raise FalconApiConfigError(
            f"The annotated method needs to have one of "
            f"the typical request methods: {', '.join(func_name_method_mapping.keys())}"
        )

    return OperationDocs()


def operation(
    method: HttpMethod,
    **kwargs: Unpack[OperationKwArgs],
) -> Callable[..., Any]:
    """
    Decorator for API operations.
    :param operation_id: specific openAPI operation id, if not provided the camelCased function name will be used
    :param deprecated: flag to mark the operation as deprecated in the openapi docs (default: False)
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation(method, func, **kwargs)
        setattr(func, ATTR_OPERATION, info)
        return func

    return wrap


def operation_doc(
    operation_id: str | None = None,
    docs: OperationDocs | None = None,
) -> Callable[..., Any]:
    """
    ...
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        inspect_operation_doc(func)
        return func

    return wrap
