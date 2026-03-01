import inspect
import warnings
from enum import Enum
from typing import Any, Callable, TypedDict

from pydantic import create_model
from typing_extensions import NotRequired, Unpack

import falcon_swoop.type_util as type_util
from falcon_swoop.binary import BODY_TYPES
from falcon_swoop.context import OpAsgiContext, OpContext
from falcon_swoop.error import FalconSwoopConfigError, FalconSwoopConfigWarning
from falcon_swoop.operation_spec import (
    HttpMethod,
    HttpMethodByFuncName,
    OpExample,
    OpFuncInput,
    OpFuncOutput,
    OpFuncOutputType,
    OpFuncParam,
    OpFuncParamInput,
    OpFuncSpec,
    OpInfo,
    OpInfoWithSpec,
    OpRequestDoc,
    OpResponseDocByHttpCode,
)
from falcon_swoop.output import OpOutput
from falcon_swoop.param import OpParam, OpParamKind, OpParamType

ATTR_OPERATION = "operation"


def _find_param_type(
    param: OpParam,
    annotation: Any,
    empty_val: Any,
    param_error_hint: str,
) -> tuple[OpParamType, bool]:
    optional = False
    if annotation == empty_val:
        raise FalconSwoopConfigError(
            f"{param_error_hint} requires type annotation, possible types are {param.allow_types}"
        )
    if type_util.is_union_type(annotation):
        unpacked_opt = type_util.unpack_optional_type(annotation)
        if unpacked_opt.is_optional_for_single_type:
            if param.allow_optional:
                annotation = unpacked_opt.types_without_none[0]
                optional = True
            else:
                raise FalconSwoopConfigError(f"{param_error_hint} cannot be optional")
        else:
            raise FalconSwoopConfigError(f"{param_error_hint} cannot be a union")

    unpacked_lit = type_util.unpack_literal_type(annotation)
    if unpacked_lit.is_literal:
        allowed_literal_types = (str, int, bool)
        if not unpacked_lit.has_only_values_of_type(allowed_literal_types):
            raise FalconSwoopConfigError(
                f"{param_error_hint} must only have literal values of type {allowed_literal_types}"
            )
    elif type_util.safe_issubclass(annotation, Enum):
        if not issubclass(annotation, str):
            raise FalconSwoopConfigError(
                f"{param_error_hint} must be a string enum to be usable, either subclass "
                f"from str and Enum or use StrEnum"
            )
    elif annotation not in param.allow_types:
        raise FalconSwoopConfigError(
            f"{param_error_hint} has unsupported type annotation {annotation}, possible types are {param.allow_types}"
        )
    return annotation, optional


def _find_params(
    signature: inspect.Signature,
    param_names: set[str],
    kind: OpParamKind,
    operation_id: str,
    case_sensitive: bool = True,
) -> tuple[OpFuncParamInput | None, set[str]]:
    param_inputs = []

    for param_name in param_names:
        input_argument = signature.parameters[param_name]
        if input_argument.default is None or input_argument.default == signature.empty:
            continue
        if not isinstance(input_argument.default, OpParam):
            continue
        param: OpParam = input_argument.default
        if param.kind != kind:
            continue
        param_kind_str = param.kind.capitalize()
        error_start = f"{param_kind_str} parameter {input_argument.name}"
        annotation, optional = _find_param_type(
            param=param,
            annotation=input_argument.annotation,
            empty_val=signature.empty,
            param_error_hint=error_start,
        )
        if optional and param.has_default_value and not param.has_none_as_default_value:
            warnings.warn(
                f"{error_start} is type hinted as optional, but will never be None because of default value",
                FalconSwoopConfigWarning,
            )
        param_input = OpFuncParam(
            name=param_name,
            annotation=annotation,
            annotation_orig=input_argument.annotation,
            info=param.field_info,
            optional=optional,
        )
        if not case_sensitive:
            input_name = param_input.input_name
            if not (input_name.islower() or input_name.isupper()):
                alias_hint = " (see alias)" if param_input.uses_alias else ""
                warnings.warn(
                    f"{error_start} has mixed case{alias_hint}, but {param_kind_str} parameters are "
                    "case insensitive, it's recommend to use either lowercase or uppercase only",
                    FalconSwoopConfigWarning,
                )
        param_inputs.append(param_input)

    if len(param_inputs) == 0:
        return None, set()

    used_param_names = {pi.name for pi in param_inputs}
    param_model_name = f"{operation_id}{kind.lower().capitalize()}Params"
    param_type = create_model(param_model_name, **{pi.name: (pi.annotation_orig, pi.info) for pi in param_inputs})  # type: ignore[call-overload]
    func_input = OpFuncParamInput(
        model_type=param_type,
        param_by_name={pi.name: pi for pi in param_inputs},
        param_by_input_name={pi.input_name: pi for pi in param_inputs},
        case_sensitive=case_sensitive,
    )
    return func_input, used_param_names


def _find_context_input(
    signature: inspect.Signature,
    param_names: set[str],
    is_sync: bool,
) -> str | None:
    expected_type = OpContext if is_sync else OpAsgiContext
    incorrect_type = OpAsgiContext if is_sync else OpContext

    context_param_name: str | None = None
    for param_name in param_names:
        input_argument = signature.parameters[param_name]
        input_type = input_argument.annotation

        if input_type == incorrect_type:
            operation_kind = "synchronous" if is_sync else "asynchronous"
            raise FalconSwoopConfigError(
                f"Argument {param_name} has type {input_type}, but expected {expected_type} "
                f"since the operation is {operation_kind}"
            )

        if input_type == expected_type:
            if context_param_name is not None:
                raise FalconSwoopConfigError(
                    f"Duplicated context parameter, {context_param_name} already receives the operation context, "
                    f"{param_name} should be removed"
                )
            context_param_name = param_name

    return context_param_name


class OperationKwArgs(TypedDict):  # noqa: D101
    operation_id: NotRequired[str]
    summary: NotRequired[str]
    description: NotRequired[str]
    tags: NotRequired[list[str]]
    accept: NotRequired[str | list[str]]
    require_valid_content_type: NotRequired[bool]
    deprecated: NotRequired[bool]
    default_status: NotRequired[int | tuple[int, str]]
    request_example: NotRequired[OpExample]
    request_examples: NotRequired[dict[str, OpExample]]
    request_examples_by_mime: NotRequired[dict[str, dict[str, OpExample]]]
    response_content_type: NotRequired[str]  # TODO: allow also list like for accept?
    response_example: NotRequired[OpExample]
    response_examples: NotRequired[dict[str, OpExample]]
    more_response_docs: NotRequired[OpResponseDocByHttpCode]


def _get_operation_id_or_default(operation_id: str | None, func: Callable[..., Any]) -> str:
    if operation_id is not None:
        return operation_id
    func_name_parts = func.__name__.split("_")
    return "".join([func_name_parts[0]] + [p.capitalize() for p in func_name_parts[1:]])


def inspect_function(  # noqa: D103
    func: Callable[..., Any],
    op_id: str,
    accept: str | list[str] | None,
    response_ct: str | None,
) -> OpFuncSpec:
    signature = inspect.signature(func)
    is_sync = not inspect.iscoroutinefunction(func)

    # --- http request params of various sort
    input_params = signature.parameters.keys() - {"self"}

    header_input, header_params = _find_params(signature, input_params, OpParamKind.HEADER, op_id, case_sensitive=False)
    query_input, query_params = _find_params(signature, input_params, OpParamKind.QUERY, op_id)
    path_input, path_params = _find_params(signature, input_params, OpParamKind.PATH, op_id)
    input_params.difference_update(header_params | query_params | path_params)

    context_input_name = _find_context_input(signature, input_params, is_sync=is_sync)
    if context_input_name is not None:
        input_params.discard(context_input_name)

    # --- http request body
    op_input = None
    if len(input_params) == 1:
        param = signature.parameters[input_params.pop()]
        param_annotation = param.annotation
        param_type = param.annotation
        optional = False

        if type_util.is_union_type(param_annotation):
            unpacked = type_util.unpack_optional_type(param_annotation)
            if unpacked.is_optional_for_single_type:
                param_type = unpacked.types_without_none[0]
                optional = True
            else:
                raise FalconSwoopConfigError(f"Operation input parameter {param.name} cannot be a union")

        if not type_util.safe_issubclass(param_type, BODY_TYPES):
            raise FalconSwoopConfigError(
                f"Operation input parameter {param.name} needs to be one of {BODY_TYPES}, bot got {param_type}"
            )
        if isinstance(accept, str):
            accept = [accept]
        op_input = OpFuncInput(
            name=param.name,
            dtype=param_type,
            optional=optional,
            accept=OpFuncInput.parse_accept_config(accept, param_type),
        )
        op_input.check_binary_dtype(is_sync)

    elif len(input_params) > 1:
        raise FalconSwoopConfigError(f"More than 1 parameter found that could be http body: {','.join(input_params)}")

    # --- http response body
    output_candidate = signature.return_annotation
    hinted_wrapper = False
    if output_candidate == signature.empty:
        output_candidate = None

    if type_util.is_generic_type(output_candidate, OpOutput):
        output_candidate = type_util.unpack_generic_type(output_candidate, none_type_to_none=True)[0]
        hinted_wrapper = True
    elif type_util.safe_issubclass(output_candidate, OpOutput):
        raise FalconSwoopConfigError(
            f"The payload type for {OpOutput.__name__} is missing, "
            f"the type hint should be {OpOutput.__name__}[<return_type>]"
        )

    output_type = None
    if output_candidate is not None:
        if type_util.is_union_type(output_candidate):
            raise FalconSwoopConfigError("Return type cannot be a union or optional")
        if not type_util.safe_issubclass(output_candidate, BODY_TYPES):
            raise FalconSwoopConfigError(f"Return type needs to be one of {BODY_TYPES}, bot got {output_candidate}")
        output_type = OpFuncOutputType(
            dtype=output_candidate,
            content_type=OpFuncOutputType.parse_content_type_config(response_ct, output_candidate),
        )
        output_type.check_binary_dtype(is_sync)
    op_output = OpFuncOutput(
        output=output_type,
        hinted_wrapper=hinted_wrapper,
    )

    return OpFuncSpec(
        func_input=op_input,
        func_output=op_output,
        query_input=query_input,
        path_input=path_input,
        header_input=header_input,
        context_input_name=context_input_name,
    )


def inspect_operation(  # noqa: D103
    method: HttpMethod,
    func: Callable[..., Any],
    **kwargs: Unpack[OperationKwArgs],
) -> OpInfoWithSpec:
    op_id = _get_operation_id_or_default(kwargs.get("operation_id"), func)
    response_ct = kwargs.get("response_content_type")

    if func.__name__ in HttpMethodByFuncName:
        raise FalconSwoopConfigError(
            f"The responder method {func.__name__} is reserved and cannot be decorated, please use another name."
            f"If you want to add documentation to a falcon responder method use @{operation_doc.__name__} instead."
        )

    func_spec = inspect_function(
        func,
        op_id=op_id,
        accept=kwargs.get("accept"),
        response_ct=response_ct,
    )
    op_input = func_spec.func_input

    request_doc: OpRequestDoc | None = None
    if op_input is not None:
        request_doc = op_input.to_doc(
            example=kwargs.get("request_example"),
            examples=kwargs.get("request_examples"),
            examples_by_mime=kwargs.get("request_examples_by_mime"),
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
    response_doc = func_spec.func_output.to_doc(description=resp_desc)
    response_docs = {resp_status: response_doc}
    more_response_docs = kwargs.get("more_response_docs", {})
    if resp_status in more_response_docs:
        raise FalconSwoopConfigError(
            f"Response docs for default HTTP status code {resp_status} are generated, cannot be provided"
        )
    response_docs.update(more_response_docs)

    return OpInfoWithSpec(
        method=method,
        operation_id=op_id,
        summary=kwargs.get("summary"),
        description=kwargs.get("description"),
        tags=kwargs.get("tags", []),
        deprecated=kwargs.get("deprecated", False),
        request_doc=request_doc,
        response_docs=response_docs,
        func=func,
        # ---
        func_spec=func_spec,
        default_status_code=resp_status,
        default_content_type=response_ct,
        require_valid_content_type=kwargs.get("require_valid_content_type", True),
    )


def operation(method: HttpMethod, **kwargs: Unpack[OperationKwArgs]) -> Callable[..., Any]:
    """Turn a method of a falcon resource into a falcon-swoop API operation.

    Note that this decorator only works on methods of ``ApiBaseResource``. Works for both sync and async operations.
    Do *not* use a falcon responder method, such as ``on_post``, directly, instead use a name that describes
    the operation, e.g. ``add_discussion_comment``. For input and output type hint your pydantic classes.

    For detailed documentation and examples check the project repository. Here is a quick start example::

        from falcon_swoop import ApiBaseResource, operation, path_param
        from pydantic import BaseModel
        from typing import Literal

        class NewCommentInput(BaseModel):
            message: str
            source: Literal["web", "ios", "android]

        class NewCommentOutput(BaseModel):
            new_comment_id: int

        class DiscussionCommentResource(ApiBaseResource):
            def __init__(self) -> None:
                super().__init__("/discussion/{discussion_id}/comment")

            @operation(method="POST")
            def add_discussion_comment(
                comment_data: NewCommentInput,
                discussion_id: int = path_param(),
            ) -> NewCommentOutput:
                # implement operation here


    :param method: HTTP method required in request
    :param operation_id: specific OpenAPI operation id (default: the camelCased name of the decorated function)
    :param summary: optional summary for OpenAPI operation (default: ``None``)
    :param description: optional description for OpenAPI operation (default: ``None``)
    :param tags: optional tags for OpenAPI operation (default: ``[]``)
    :param accept: accepted content types for requests to this operation (default: inferred from input type)
    :param require_valid_content_type: whether to require clients to send a content type compatible with ``accept``
        and return 406 if not (default ``True``)
    :param deprecated: flag to mark the operation as deprecated in the openapi docs (default: ``False``)
    :param default_status: status code and description for the default case (default: ``(200,"ok")``)
    :param request_example: request example with title "default" for the default request (default: no example)
    :param request_examples: request examples by title for the default request
        (default: ``{}``, example: ``{"scenario_a":example_request...}``)
    :param request_examples_by_mime: request examples by mime and title
        (default: ``{}``, example: ``{"application/yaml":{"scenario_a":example_request...},...}``)
    :param response_content_type: response content type for the default case (default: inferred from return type)
    :param response_example: response example with title "default" for the default response (default: no example)
    :param response_examples: response examples by title for the default response
        (default: ``{}``, example: ``{"scenario_a":example_response...}``)
    :param more_response_docs: additional rich response documentation, for example other status codes
        (default: no additional response documentation)
    """

    def mark_func(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation(method, func, **kwargs)
        setattr(func, ATTR_OPERATION, info)
        return func

    return mark_func


class OperationDocKwArgs(TypedDict):  # noqa: D101
    operation_id: NotRequired[str]
    summary: NotRequired[str]
    description: NotRequired[str]
    tags: NotRequired[list[str]]
    deprecated: NotRequired[bool]
    request_doc: NotRequired[OpRequestDoc]
    response_docs: NotRequired[OpResponseDocByHttpCode]


def inspect_operation_doc(  # noqa: D103
    func: Callable[..., Any],
    **kwargs: Unpack[OperationDocKwArgs],
) -> OpInfo:
    operation_id = _get_operation_id_or_default(kwargs.get("operation_id"), func)
    method = HttpMethodByFuncName.get(func.__name__)
    if method is None:
        raise FalconSwoopConfigError(
            f"The decorated method needs to have one of "
            f"the falcon request methods: {', '.join(HttpMethodByFuncName.keys())}"
        )

    return OpInfo(
        method=method,
        operation_id=operation_id,
        summary=kwargs.get("summary"),
        description=kwargs.get("description"),
        tags=kwargs.get("tags", []),
        deprecated=kwargs.get("deprecated", False),
        request_doc=kwargs.get("request_doc"),
        response_docs=kwargs.get("response_docs", {}),
        func=func,
    )


def operation_doc(**kwargs: Unpack[OperationDocKwArgs]) -> Callable[..., Any]:
    """Add documentation to a method of a falcon resource for inclusion in the OpenAPI spec.

    Note that this decorator only works on methods of ``ApiBaseResource``. Works for both sync and async operations.
    Use this on falcon responder methods, such as ``on_post`` that you don't want to or can't decorate with
    ``@operation``, it allows adding documentation that will be part of the OpenAPI spec.

    For detailed documentation and examples check the project repository. Here is a quick start example::

        from typing import Literal
        from falcon_swoop import ApiBaseResource, operation_doc, OpRequestDoc, OpTypeDoc

        class ComplexResource(ApiBaseResource):
            def __init__(self) -> None:
                super().__init__("/complex/operation")

            @operation_doc(
                operation_id="complexOperation",
                tags=["multiMediaUpload"],
                request_doc=OpRequestDoc(
                    by_mime={"multipart/form-data": OpTypeDoc.with_default_example(example="raw_bytes_)}
                )
                response_docs={
                   200: OpRequestDoc(by_mime={"plain/text": OpTypeDoc.with_default_example(example="ok")}),
                   400: OpRequestDoc(by_mime={"plain/text": OpTypeDoc.with_default_example(example="bad_encoding")}),
                }
            )
            def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
                # complex operation here

    :param operation_id: specific OpenAPI operation id (default: the camelCased name of the decorated function)
    :param summary: optional summary for OpenAPI operation (default: ``None``)
    :param description: optional description for OpenAPI operation (default: ``None``)
    :param tags: optional tags for OpenAPI operation (default: ``[]``)
    :param deprecated: flag to mark the operation as deprecated in the openapi docs (default: ``False``)
    :param request_doc: optional documentation of the request (default: no documentation)
    :param response_docs: optional documentation of responses by http status codes (default: no documentation)
    """

    def mark_func(func: Callable[..., Any]) -> Callable[..., Any]:
        info = inspect_operation_doc(func, **kwargs)
        setattr(func, ATTR_OPERATION, info)
        return func

    return mark_func
