import collections
import warnings
from dataclasses import dataclass
from typing import Any, Generator, Mapping

import falcon
from pydantic import BaseModel, ValidationError

from falcon_api.error import FalconApiConfigError
from falcon_api.operation import ATTR_OPERATION, HttpMethod, OperationInfo
from falcon_api.route import ApiRoute


@dataclass
class RequestContext:
    req: falcon.Request
    resp: falcon.Response


class ApiBaseResource:

    def __init__(self, route: str):
        self.api_route = ApiRoute(route)
        self.__context: RequestContext | None = None
        self.__operation_by_method = self.__setup()

    def api_ops(self) -> Generator[OperationInfo, None, None]:
        for op in self.__operation_by_method.values():
            yield op

    def __check_operation_config(
        self, operations_by_method: dict[HttpMethod, list[OperationInfo]]
    ) -> dict[HttpMethod, OperationInfo]:
        for method, ops in operations_by_method.items():
            if len(ops) > 1:
                names = ", ".join([op.func_name for op in ops])
                raise FalconApiConfigError(f"Multiple functions are defined as {method} operation: {names}")

        if len(operations_by_method) == 0:
            raise FalconApiConfigError("Found no operation, at least one is required")

        return {method: ops[0] for method, ops in operations_by_method.items()}

    def __check_path_parameter_match(self, operation_by_method: dict[HttpMethod, OperationInfo]) -> None:
        path_param_exp = self.api_route.param_names
        for method, op in operation_by_method.items():
            path_param_act = set()
            if op.path_input is not None:
                path_param_act = set(
                    [name if info.alias is None else info.alias for name, info in op.path_input.model_fields.items()]
                )

            missing = path_param_exp.difference(path_param_act)
            too_much = path_param_act.difference(path_param_exp)
            if len(missing) > 0 or len(too_much) > 0:
                raise FalconApiConfigError(
                    f"Found mismatch for path parameters defined for operation {method}\n"
                    f"missing parameters: {missing}\n"
                    f"additional parameters: {too_much}"
                )

    def __setup(self) -> dict[HttpMethod, OperationInfo]:
        operations_by_method: dict[HttpMethod, list[OperationInfo]] = collections.defaultdict(list)

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

        operation_by_method = self.__check_operation_config(operations_by_method)
        self.__check_path_parameter_match(operation_by_method)
        return operation_by_method

    @property
    def ctx(self) -> RequestContext:
        if self.__context is None:
            raise RuntimeError("No active request, so no context is available")
        return self.__context

    def __collect_typed_kwargs(
        self, input_kwargs: Mapping[str, Any], model_type: type[BaseModel] | None, case_sensitive: bool = True
    ) -> dict[str, Any]:
        if model_type is None:
            return {}
        if not case_sensitive:
            _input_kwargs = {k.lower(): v for k, v in input_kwargs.items()}
            if len(_input_kwargs) != len(input_kwargs):
                warnings.warn("Unexpectedly lost data due to lowercasing")
            _input_kwargs2 = {}
            for name, info in model_type.model_fields.items():
                input_name: str = info.alias or name
                input_name_lowered = input_name.lower()
                if input_name_lowered in _input_kwargs:
                    _input_kwargs2[input_name] = _input_kwargs[input_name_lowered]
            input_kwargs = _input_kwargs2
        try:
            model: BaseModel = model_type(**input_kwargs)
        except ValidationError as e:
            raise falcon.HTTPBadRequest(description=str(e))
        return model.model_dump(by_alias=False)

    def __on_request(
        self,
        method: HttpMethod,
        req: falcon.Request,
        resp: falcon.Response,
        **path_params: Any,
    ) -> None:
        op: OperationInfo | None = self.__operation_by_method.get(method)
        if op is None:
            op_keys = self.__operation_by_method.keys()
            raise falcon.HTTPMethodNotAllowed(op_keys)
        self.__context = RequestContext(req, resp)

        kwargs = {}
        kwargs.update(self.__collect_typed_kwargs(req.params, op.query_input))
        kwargs.update(self.__collect_typed_kwargs(path_params, op.path_input))
        kwargs.update(self.__collect_typed_kwargs(req.headers, op.header_input, case_sensitive=False))

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

    def on_get(self, req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
        self.__on_request("GET", req, resp, **path_params)

    def on_post(self, req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
        self.__on_request("POST", req, resp, **path_params)

    def on_put(self, req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
        self.__on_request("PUT", req, resp, **path_params)

    def on_patch(self, req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
        self.__on_request("PATCH", req, resp, **path_params)

    def on_delete(self, req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
        self.__on_request("DELETE", req, resp, **path_params)
