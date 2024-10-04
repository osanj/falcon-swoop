from dataclasses import dataclass
import collections
from typing import Any, Dict, TypeVar, Literal, Callable, List, Type
import inspect

import falcon
from pydantic import BaseModel


@dataclass
class RequestContext:
    req: falcon.Request
    resp: falcon.Response


T_METHOD = Literal["GET", "POST"]
T_MODEL = TypeVar("T_MODEL", bound=BaseModel)
ATTR_OPERATION = "operation"


class SimpleApiError(Exception):
    pass


class SimpleApiConfigError(SimpleApiError):
    pass


@dataclass
class OperationJsonInput:
    name: str
    model: Type[T_MODEL]


# class OperationQueryParam:
#     name: str
#     default: Any | None
#     optional: bool


@dataclass
class OperationInfo:
    method: T_METHOD
    operation_id: str | None

    func: Callable
    func_input: OperationJsonInput | None
    func_output_model: Type[T_MODEL] | None

    @property
    def func_name(self) -> str:
        return self.func.__name__


def operation(method: T_METHOD, operation_id: str | None = None) -> Callable:
    def wrap(func: Callable) -> Callable:
        signature = inspect.signature(func)
        op_input = None
        t_output = None

        input_params = signature.parameters.keys() - {"self"}
        if len(input_params) == 1:
            param = signature.parameters[input_params.pop()]
            param_type = param.annotation
            if not issubclass(param_type, BaseModel):
                raise SimpleApiConfigError(f"Parameter type of {param.name} needs to be a subclass of {BaseModel.__name__}")
            op_input = OperationJsonInput(param.name, param_type)
        elif len(input_params) > 1:
            raise SimpleApiConfigError("More than 1 parameter found")

        if signature.return_annotation != signature.empty:
            if not issubclass(signature.return_annotation, BaseModel):
                raise SimpleApiConfigError(f"Return type needs to be a subclass of {BaseModel.__name__}")
            t_output = signature.return_annotation

        info = OperationInfo(
            method=method,
            operation_id=operation_id,
            func=func,
            func_input=op_input,
            func_output_model=t_output,
        )
        setattr(func, ATTR_OPERATION, info)
        return func
    return wrap


class BaseResource:

    def __init__(self, route: str, tag: str | None = None):
        self.route = route
        self.tag = tag
        self.__context: RequestContext | None = None
        self.__operations = self.__setup()

    def __setup(self) -> Dict[T_METHOD, OperationInfo]:
        operations_by_method: Dict[T_METHOD, List[OperationInfo]] = collections.defaultdict(list)

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
                raise SimpleApiConfigError(f"Multiple functions are defined as {method} operation: {names}")

        if len(operations_by_method) == 0:
            raise SimpleApiConfigError("Found no operation, at least one is required")

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
