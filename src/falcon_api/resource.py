import collections
from dataclasses import dataclass

import falcon
from pydantic import BaseModel, ValidationError

from falcon_api.error import FalconApiConfigError
from falcon_api.operation import ATTR_OPERATION, T_METHOD, OperationInfo


@dataclass
class RequestContext:
    req: falcon.Request
    resp: falcon.Response


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
            op_keys = self.__operations.keys()
            raise falcon.HTTPMethodNotAllowed(op_keys)
        self.__context = RequestContext(req, resp)

        kwargs = {}

        if op.query_input is not None:
            try:
                query_data: BaseModel = op.query_input(**req.params)
            except ValidationError as e:
                raise falcon.HTTPBadRequest(description=str(e))
            kwargs.update(query_data.model_dump(by_alias=True))

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

    def on_put(self, req: falcon.Request, resp: falcon.Response) -> None:
        self.__on_request(req, resp)

    def on_patch(self, req: falcon.Request, resp: falcon.Response) -> None:
        self.__on_request(req, resp)

    def on_delete(self, req: falcon.Request, resp: falcon.Response) -> None:
        self.__on_request(req, resp)
