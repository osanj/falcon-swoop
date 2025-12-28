import collections
import warnings
from dataclasses import dataclass
from typing import Any, Generator, Mapping

import falcon
from pydantic import BaseModel, ValidationError

from falcon_swoop.error import FalconSwoopConfigError, FalconSwoopWarning
from falcon_swoop.operation import ATTR_OPERATION, HttpMethod, OpInfo, OpInfoWithSpec, OpFuncParamInput
from falcon_swoop.route import ApiRoute


@dataclass
class RequestContext:
    req: falcon.Request
    resp: falcon.Response


class ApiBaseResource:

    def __init__(self, route: str):
        self.api_route = ApiRoute(route)
        self.__context: RequestContext | None = None
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

    def __patch_op(self, method: HttpMethod) -> None:
        method_name = f"on_{method}".lower()
        if getattr(self, method_name, None) is not None:
            raise FalconSwoopConfigError(f"Decorated {method} operation is invalid because method {method_name} exists")

        def forward(req: falcon.Request, resp: falcon.Response, **path_params: Any) -> None:
            self.__on_request(method, req, resp, **path_params)

        setattr(self, method_name, forward)

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
                self.__patch_op(method)
        return operation_by_method

    @property
    def ctx(self) -> RequestContext:
        if self.__context is None:
            raise RuntimeError("No active request, so no context is available")
        return self.__context

    def __collect_typed_kwargs(
        self, input_kwargs_: Mapping[str, Any], param_input: OpFuncParamInput | None, case_sensitive: bool = True
    ) -> dict[str, Any]:
        if param_input is None:
            return {}
        input_kwargs = dict(input_kwargs_)
        model_type = param_input.model_type
        input_name: str
        if not case_sensitive:
            _input_kwargs = {k.lower(): v for k, v in input_kwargs.items()}
            if len(_input_kwargs) != len(input_kwargs):
                warnings.warn("Unexpectedly lost data due to lowercasing", FalconSwoopWarning)
            _input_kwargs2 = {}
            for name, info in model_type.model_fields.items():
                input_name = info.alias or name
                input_name_lowered = input_name.lower()
                if input_name_lowered in _input_kwargs:
                    _input_kwargs2[input_name] = _input_kwargs[input_name_lowered]
            input_kwargs = _input_kwargs2
        for name, info in model_type.model_fields.items():
            input_name = info.alias or name
            optional = param_input.param_by_name[name].optional
            if input_name not in input_kwargs and optional:
                input_kwargs[input_name] = None
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
        op: OpInfo | None = self.__operation_by_method.get(method)
        if op is None:
            raise ValueError(f"Expected object of subtype {OpInfoWithSpec.__name__}")
        if not isinstance(op, OpInfoWithSpec):
            raise ValueError(f"Expected object of subtype {OpInfoWithSpec.__name__}")

        self.__context = RequestContext(req, resp)

        spec = op.func_spec
        kwargs = {}
        kwargs.update(self.__collect_typed_kwargs(req.params, spec.query_input))
        kwargs.update(self.__collect_typed_kwargs(path_params, spec.path_input))
        kwargs.update(self.__collect_typed_kwargs(req.headers, spec.header_input, case_sensitive=False))

        if spec.func_input is not None:
            if spec.func_input.optional:
                media = req.get_media(default_when_empty=None)
                if media is None:
                    data = None
                else:
                    data = spec.func_input.model_type(**media)
            else:
                # calling req.get_media() again to maintain default falcon behavior for empty body when JSON is expected
                data = spec.func_input.model_type(**req.get_media())
            kwargs[spec.func_input.name] = data

        data_output = op.func(self, **kwargs)
        if data_output is not None:
            if not isinstance(data_output, BaseModel):
                raise ValueError(f"Expected object of subtype {BaseModel.__name__}")
            resp.media = data_output.model_dump()
        resp.status = falcon.HTTP_OK

        self.__context = None
