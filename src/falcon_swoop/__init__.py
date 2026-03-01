"""Package for building typed API operations in falcon using pydantic models. Automatic OpenAPI generation included."""

from falcon_swoop.context import OpContext, OpAsgiContext
from falcon_swoop.error import FalconSwoopError, FalconSwoopConfigError, FalconSwoopWarning, FalconSwoopConfigWarning
from falcon_swoop.param import header_param, path_param, query_param
from falcon_swoop.resource import ApiBaseResource
from falcon_swoop.openapi.gen import OpenApiGenerator, OpenApiGeneratorResult, OpenApiGeneratorSettings
from falcon_swoop.operation import operation, operation_doc
from falcon_swoop.operation_spec import OpExample, OpTypeDoc, OpRequestDoc, OpResponseDoc
from falcon_swoop.output import OpOutput
from falcon_swoop.binary import OpAsgiBinary, OpBinary

__version__ = "0.1.0"
__all__ = [
    "FalconSwoopError",
    "FalconSwoopConfigError",
    "FalconSwoopWarning",
    "FalconSwoopConfigWarning",
    "ApiBaseResource",
    "OpAsgiBinary",
    "OpBinary",
    "header_param",
    "path_param",
    "query_param",
    "OpenApiGenerator",
    "OpenApiGeneratorResult",
    "OpenApiGeneratorSettings",
    "operation",
    "operation_doc",
    "OpAsgiContext",
    "OpContext",
    "OpExample",
    "OpRequestDoc",
    "OpResponseDoc",
    "OpOutput",
    "OpTypeDoc",
]
