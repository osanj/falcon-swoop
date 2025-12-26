import inspect
from dataclasses import dataclass
from typing import Any, Literal, Callable, Sequence

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
    accept: list[MimeType]

    func: Callable[..., Any]
    func_input: OperationApiModelInput | None
    query_input: type[BaseModel] | None
    path_input: type[BaseModel] | None
    # allow raw input?
    # accept mime type?
    func_output_model: type[BaseModel] | None

    header_params: list[OperationApiParamInput]
    # path_params: list[OperationApiParamInput]
    # query_params: list[OperationApiParamInput]

    docs: OperationDocs | None

    @property
    def func_name(self) -> str:
        return self.func.__name__


def inspect_operation(
    func: Callable[..., Any],
    method: HttpMethod,
    operation_id: str | None = None,
    accept: Sequence[MimeType] = ("application/json",),
    docs: OperationDocs | None = None,
) -> OperationInfo:
    signature = inspect.signature(func)
    op_input = None
    t_output = None

    header_params: list[OperationApiParamInput] = []
    path_params: list[OperationApiParamInput] = []
    query_params: list[OperationApiParamInput] = []

    input_params = signature.parameters.keys() - {"self"}
    used_param_names = []
    for param_name in input_params:
        param = signature.parameters[param_name]
        if param.default is None or param.default == signature.empty:
            continue
        if not isinstance(param.default, Param):
            continue
        default: Param = param.default
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
        if default.kind == ParamKind.HEADER:
            header_params.append(param_input)
        elif default.kind == ParamKind.PATH:
            path_params.append(param_input)
        elif default.kind == ParamKind.QUERY:
            query_params.append(param_input)
        else:
            raise FalconApiConfigError(f"Unexpected error, cannot handle {type(param.default)}")
        used_param_names.append(param_name)

    input_params = input_params.difference(set(used_param_names))

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

    if operation_id is None:
        func_name_parts = func.__name__.split("_")
        operation_id = "".join([func_name_parts[0]] + [p.capitalize() for p in func_name_parts[1:]])

    query_input = None
    if len(query_params) > 0:
        query_input = create_model(
            f"{operation_id}QueryParams", **{qp.name: (qp.annotation, qp.info) for qp in query_params}
        )  # type: ignore[call-overload]

    path_input = None
    if len(path_params) > 0:
        path_input = create_model(
            f"{operation_id}PathParams", **{qp.name: (qp.annotation, qp.info) for qp in path_params}
        )  # type: ignore[call-overload]

    return OperationInfo(
        method=method,
        operation_id=operation_id,
        accept=list(accept),
        func=func,
        func_input=op_input,
        func_output_model=t_output,
        query_input=query_input,
        path_input=path_input,
        header_params=header_params,
        docs=docs,
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
    operation_id: str | None = None,
    accept: Sequence[MimeType] = ("application/json",),
    docs: OperationDocs | None = None,
) -> Callable[..., Any]:
    """
    ...
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation(
            func,
            method=method,
            operation_id=operation_id,
            accept=accept,
            docs=docs,
        )
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
