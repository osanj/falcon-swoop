import collections
import functools
import inspect
from dataclasses import dataclass
from typing import TypeVar, Literal, Callable, Type, Sequence

import falcon
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from falcon_api.model import Param


@dataclass
class RequestContext:
    req: falcon.Request
    resp: falcon.Response


T_METHOD = Literal["GET", "POST"]
T_MODEL = TypeVar("T_MODEL", bound=BaseModel)
T_MIME = Literal["application/json"]
ATTR_OPERATION = "operation"


class FalconApiError(Exception):
    pass


class FalconApiConfigError(FalconApiError):
    pass


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
                raise FalconApiConfigError(
                    f"Parameter type of {param.name} needs to be a subclass of {BaseModel.__name__}"
                )
            op_input = OperationApiModelInput(param.name, param_type)
        elif len(input_params) > 1:
            raise FalconApiConfigError("More than 1 parameter found")

        if signature.return_annotation != signature.empty:
            if not issubclass(signature.return_annotation, BaseModel):
                raise FalconApiConfigError(f"Return type needs to be a subclass of {BaseModel.__name__}")
            t_output = signature.return_annotation

        info = OperationInfo(
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
        setattr(func, ATTR_OPERATION, info)
        return func

    return wrap


def documented_operation(
    operation_id: str | None = None,
    docs: OperationDocs | None = None,
) -> Callable:
    """
    ...
    """
    func_name_method_mapping: dict[str, T_METHOD] = {
        "on_get": "GET",
        "on_post": "POST",
    }

    def wrap(func: Callable) -> Callable:
        method = func_name_method_mapping.get(func.__name__)
        if method is None:
            raise FalconApiConfigError(
                f"The {documented_operation.__name__} decorator may only be applied "
                f"to the common falcon methods: {', '.join(func_name_method_mapping.keys())}"
            )
        return func

    return wrap


class ApiBaseResource:

    def __init__(self, route: str, tag: str | None = None):
        self.route = route
        self.tag = tag
        self.__context: RequestContext | None = None
        self.__operations = self.__setup()

    def __setup(self) -> dict[T_METHOD, OperationInfo]:
        operations_by_method: dict[T_METHOD, list[OperationInfo]] = collections.defaultdict(list)

        for name in dir(self):
            if name.startswith("__"):
                continue
            try:
                item = getattr(self, name)
            except:
                continue
            operation_info = getattr(item, ATTR_OPERATION, None)
            if isinstance(operation_info, OperationInfo):
                operations_by_method[operation_info.method].append(operation_info)

        for method, ops in operations_by_method.items():
            if len(ops) > 1:
                names = ", ".join([op.func_name for op in ops])
                raise FalconApiConfigError(f"Multiple functions are defined as {method} operation: {names}")

        if len(operations_by_method) == 0:
            raise FalconApiConfigError("Found no operation, at least one is required")

        return {method: ops[0] for method, ops in operations_by_method.items()}

    @property
    def ctx(self) -> RequestContext:
        if self.__context is None:
            raise RuntimeError("No active request, so no context is available")
        return self.__context

    def __on_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        op: OperationInfo | None = self.__operations.get(req.method)
        if op is None:
            return
        self.__context = RequestContext(req, resp)

        kwargs = {}
        if op.func_input is not None:
            data = op.func_input.model(**req.get_media())
            kwargs[op.func_input.name] = data

        data_output = op.func(self, **kwargs)
        if data_output is not None:
            if not isinstance(data_output, BaseModel):
                raise ValueError(f"Expected object of subtype {BaseModel.__name__}")
            resp.media = data_output.model_dump()
        resp.status = falcon.HTTP_OK

        self.__context = None

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        self.__on_request(req, resp)

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        self.__on_request(req, resp)
