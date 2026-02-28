import collections
import warnings
from typing import Any, Generator, Mapping

import falcon
import falcon.asgi
from pydantic import BaseModel, ValidationError

from falcon_swoop.context import OpContext, OpAsgiContext
from falcon_swoop.error import FalconSwoopConfigError, FalconSwoopWarning
from falcon_swoop.binary import OpBinary, OpAsgiBinary
from falcon_swoop.operation import ATTR_OPERATION, HttpMethod, OpInfo, OpInfoWithSpec, OpFuncParamInput
from falcon_swoop.output import OpOutput
from falcon_swoop.route import ApiRoute


class ApiBaseResource:

    def __init__(self, route: str):
        self.api_route = ApiRoute(route)
        self.__operation_by_method = self.__setup()

    def api_ops(self) -> Generator[OpInfo, None, None]:
        for op in self.__operation_by_method.values():
            yield op

    def __check_operation_config(
        self, operations_by_method: dict[HttpMethod, list[OpInfo]]
    ) -> dict[HttpMethod, OpInfo]:
        for method, ops in operations_by_method.items():
            if len(ops) > 1:
                names = ", ".join([op.func_name for op in ops])
                raise FalconSwoopConfigError(f"Multiple functions are defined as {method} operation: {names}")

        if len(operations_by_method) == 0:
            raise FalconSwoopConfigError("Found no operation, at least one is required")

        return {method: ops[0] for method, ops in operations_by_method.items()}

    def __check_path_parameter_match(self, operation_by_method: dict[HttpMethod, OpInfo]) -> None:
        path_param_exp = self.api_route.param_names
        for method, op in operation_by_method.items():
            if not isinstance(op, OpInfoWithSpec):
                continue
            path_param_act = set()
            path_input = op.func_spec.path_input
            if path_input is not None:
                path_param_act = set(
                    [
                        name if info.alias is None else info.alias
                        for name, info in path_input.model_type.model_fields.items()
                    ]
                )

            missing = path_param_exp.difference(path_param_act)
            too_much = path_param_act.difference(path_param_exp)
            if len(missing) > 0 or len(too_much) > 0:
                raise FalconSwoopConfigError(
                    f"Found mismatch for path parameters defined for operation {method}\n"
                    f"missing parameters: {missing}\n"
                    f"additional parameters: {too_much}"
                )

    def __patch_op(self, method: HttpMethod, sync: bool = True) -> None:
        method_name = f"on_{method}".lower()
        if getattr(self, method_name, None) is not None:
            raise FalconSwoopConfigError(f"Decorated {method} operation is invalid because method {method_name} exists")

        def forward(req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
            self.__on_request(method, req, resp, **path_params)

        async def forward_async(req: falcon.asgi.Request, resp: falcon.asgi.Response, **path_params: Any) -> None:
            await self.__on_request_async(method, req, resp, **path_params)

        if sync:
            setattr(self, method_name, forward)
        else:
            setattr(self, method_name, forward_async)

    def __setup(self) -> dict[HttpMethod, OpInfo]:
        operations_by_method: dict[HttpMethod, list[OpInfo]] = collections.defaultdict(list)

        for name in dir(self):
            if name.startswith("__"):
                continue
            try:
                item = getattr(self, name)
            except:
                continue
            operation_info = getattr(item, ATTR_OPERATION, None)
            if isinstance(operation_info, OpInfo):
                operations_by_method[operation_info.method].append(operation_info)

        operation_by_method = self.__check_operation_config(operations_by_method)
        self.__check_path_parameter_match(operation_by_method)
        for method, op in operation_by_method.items():
            if isinstance(op, OpInfoWithSpec):
                self.__patch_op(method, sync=op.is_sync)
        return operation_by_method

    def __collect_typed_kwargs(
        self,
        input_kwargs_: Mapping[str, Any],
        func_input: OpFuncParamInput | None,
    ) -> dict[str, Any]:
        if func_input is None:
            return {}
        input_kwargs = dict(input_kwargs_)
        input_name: str
        if not func_input.case_sensitive:
            _input_kwargs = {k.lower(): v for k, v in input_kwargs.items()}
            if len(_input_kwargs) != len(input_kwargs):
                warnings.warn("Unexpectedly lost data due to lowercasing", FalconSwoopWarning)
            _input_kwargs2 = {}
            for name, param_input in func_input.param_by_name.items():
                input_name = param_input.input_name
                input_name_lowered = input_name.lower()
                if input_name_lowered in _input_kwargs:
                    _input_kwargs2[input_name] = _input_kwargs[input_name_lowered]
            input_kwargs = _input_kwargs2

        for name, param_input in func_input.param_by_name.items():
            input_name = param_input.input_name
            if input_name not in input_kwargs and param_input.optional:
                input_kwargs[input_name] = None
        try:
            model: BaseModel = func_input.model_type(**input_kwargs)
        except ValidationError as e:
            raise falcon.HTTPBadRequest(description=str(e))
        return model.model_dump(by_alias=False)

    def __prepare_operation(
        self, method: HttpMethod, req: falcon.Request | falcon.asgi.Request, path_params: dict[str, Any]
    ) -> tuple[OpInfoWithSpec, dict[str, Any]]:
        op: OpInfo | None = self.__operation_by_method.get(method)
        if op is None:
            raise ValueError(f"Expected object of subtype {OpInfoWithSpec.__name__}")
        if not isinstance(op, OpInfoWithSpec):
            raise ValueError(f"Expected object of subtype {OpInfoWithSpec.__name__}")

        ct = req.content_type
        fi = op.func_spec.func_input
        if ct is not None and fi is not None and op.require_valid_content_type and not fi.can_accept(ct):
            accepted_content_types = ", ".join(fi.accept)
            raise falcon.HTTPNotAcceptable(description=f"Accepted content types are: {accepted_content_types}")

        kwargs = {}
        kwargs.update(self.__collect_typed_kwargs(req.params, op.func_spec.query_input))
        kwargs.update(self.__collect_typed_kwargs(path_params, op.func_spec.path_input))
        kwargs.update(self.__collect_typed_kwargs(req.headers, op.func_spec.header_input))
        return op, kwargs

    def __finish_operation(
        self,
        op: OpInfoWithSpec,
        resp: falcon.Response | falcon.asgi.Response,
        output: Any | None,
    ) -> None:
        if not isinstance(output, OpOutput):
            output = OpOutput(payload=output)

        payload = output.payload
        if payload is None:
            pass
        elif isinstance(payload, BaseModel):
            resp.media = payload.model_dump(mode="json", by_alias=True)
        elif isinstance(payload, (OpBinary, OpAsgiBinary)):
            ct = payload.content_type or op.default_content_type
            if ct is None:
                ct = "text/plain" if payload.charset is not None else "application/octet-stream"
            if payload.charset is not None:
                ct = f"{ct}; charset={payload.charset}"
            resp.stream = payload.rio
            resp.content_length = payload.content_length
            resp.content_type = ct
        else:
            raise ValueError(f"Got payload of unsupported type: {type(payload)}")

        if output.cache_control is not None:
            resp.cache_control = output.cache_control
        if output.etag is not None:
            resp.etag = output.etag
        if output.expires is not None:
            resp.expires = output.expires
        if output.content_type is not None:
            resp.content_type = output.content_type
        resp.headers.update(output.headers)
        resp.status_code = output.status_code if output.status_code is not None else op.default_status_code

    def __on_request(
        self,
        method: HttpMethod,
        req: falcon.Request,
        resp: falcon.Response,
        **path_params: Any,
    ) -> None:
        op, kwargs = self.__prepare_operation(method=method, req=req, path_params=path_params)
        spec = op.func_spec
        if spec.context_input_name is not None:
            kwargs[spec.context_input_name] = OpContext(req, resp)
        if spec.func_input is not None:
            dtype = spec.func_input.dtype
            if issubclass(dtype, BaseModel):
                if spec.func_input.optional:
                    media = req.get_media(default_when_empty=None)
                    data = None if media is None else dtype(**media)
                else:
                    # calling req.get_media() again to maintain default falcon behavior for empty body when JSON is expected
                    data = dtype(**req.get_media())
                kwargs[spec.func_input.name] = data

            if issubclass(dtype, OpBinary):
                kwargs[spec.func_input.name] = dtype(
                    binary=req.bounded_stream,
                    content_length=req.content_length,
                    content_type=req.content_type,
                    charset=None,  # TODO: check
                )

        data_output = op.func(self, **kwargs)
        self.__finish_operation(op, resp, data_output)

    async def __on_request_async(
        self,
        method: HttpMethod,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        **path_params: Any,
    ) -> None:
        op, kwargs = self.__prepare_operation(method=method, req=req, path_params=path_params)
        spec = op.func_spec
        if spec.context_input_name is not None:
            kwargs[spec.context_input_name] = OpAsgiContext(req, resp)
        if spec.func_input is not None:
            dtype = spec.func_input.dtype
            if issubclass(dtype, BaseModel):
                if spec.func_input.optional:
                    media = await req.get_media(default_when_empty=None)
                    data = None if media is None else dtype(**media)
                else:
                    # calling req.get_media() again to maintain default falcon behavior for empty body when JSON is expected
                    media = await req.get_media()
                    data = dtype(**media)
                kwargs[spec.func_input.name] = data

            if issubclass(dtype, OpAsgiBinary):
                kwargs[spec.func_input.name] = dtype(
                    binary=req.bounded_stream,
                    content_length=req.content_length,
                    content_type=req.content_type,
                    charset=None,  # TODO: check
                )

        data_output = await op.func(self, **kwargs)
        self.__finish_operation(op, resp, data_output)
