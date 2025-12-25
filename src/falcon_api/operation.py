import inspect
from dataclasses import dataclass
from typing import TypeVar, Literal, Callable, Type, Sequence

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from falcon_api.error import FalconApiConfigError
from falcon_api.model import Param


T_METHOD = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]  # , "OPTIONS"]
T_MODEL = TypeVar("T_MODEL", bound=BaseModel)
T_MIME = Literal["application/json"]
ATTR_OPERATION = "operation"


@dataclass
class OperationApiModelInput:
    name: str
    model: Type[T_MODEL]


@dataclass
class OperationApiParamInput:
    name: str
    type: Type[bool | int | float | str]
    info: FieldInfo


@dataclass
class OperationDocs:
    pass


@dataclass
class OperationInfo:
    method: T_METHOD
    operation_id: str | None
    accept: list[T_MIME]

    func: Callable
    func_input: OperationApiModelInput | None
    # allow raw input?
    # accept mime type?
    func_output_model: type[T_MODEL] | None

    header_params: list[OperationApiParamInput]
    path_params: list[OperationApiParamInput]
    query_params: list[OperationApiParamInput]

    docs: OperationDocs | None

    @property
    def func_name(self) -> str:
        return self.func.__name__


def inspect_operation(
    func: Callable,
    method: T_METHOD,
    operation_id: str | None = None,
    accept: Sequence[T_MIME] = ("application/json",),
    docs: OperationDocs | None = None,
) -> OperationInfo:
    signature = inspect.signature(func)
    op_input = None
    t_output = None

    header_params: list[OperationApiParamInput] = []
    path_params: list[OperationApiParamInput] = []
    query_params: list[OperationApiParamInput] = []

    allowed_param_types = (bool, int, float, str)

    input_params = signature.parameters.keys() - {"self"}
    used_param_names = []
    for param_name in input_params:
        param = signature.parameters[param_name]
        if param.default is None:
            continue
        if not isinstance(param.default, Param):
            continue
        default: Param = param.default
        if param.annotation is None:
            raise FalconApiConfigError(
                f"Parameter {param.name} requires type annotation, possible types are {allowed_param_types}"
            )
        if param.annotation not in allowed_param_types:
            raise FalconApiConfigError(
                f"Parameter {param.name} has unsupported type annotation {param.annotation}, "
                f"possible types are {allowed_param_types}"
            )
        param_input = OperationApiParamInput(
            name=param_name,
            type=param.annotation,
            info=default.field_info,
        )
        if default.type == "header":
            header_params.append(param_input)
        elif default.type == "path":
            path_params.append(param_input)
        elif default.type == "query":
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

    return OperationInfo(
        method=method,
        operation_id=operation_id,
        accept=list(accept),
        func=func,
        func_input=op_input,
        func_output_model=t_output,
        header_params=header_params,
        path_params=path_params,
        query_params=query_params,
        docs=docs,
    )


def inspect_operation_doc(
    func: Callable,
) -> OperationDocs:
    func_name_method_mapping: dict[str, T_METHOD] = {
        "on_get": "GET",
        "on_post": "POST",
    }

    method = func_name_method_mapping.get(func.__name__)
    if method is None:
        raise FalconApiConfigError(
            f"The annotated method needs to have one of "
            f"the typical request methods: {', '.join(func_name_method_mapping.keys())}"
        )


def operation(
    method: T_METHOD,
    operation_id: str | None = None,
    accept: Sequence[T_MIME] = ("application/json",),
    docs: OperationDocs | None = None,
) -> Callable:
    """
    ...
    """

    def wrap(func: Callable) -> Callable:
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
) -> Callable:
    """
    ...
    """

    def wrap(func: Callable) -> Callable:
        inspect_operation_doc(func)
        return func

    return wrap
