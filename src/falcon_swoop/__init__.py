"""Package for building typed API operations in falcon using pydantic models. Automatic OpenAPI generation included."""

from falcon_swoop.app import SwoopApp
from falcon_swoop.binary import OpAsgiBinary, OpBinary
from falcon_swoop.context import OpAsgiContext, OpContext
from falcon_swoop.error import FalconSwoopConfigError, FalconSwoopConfigWarning, FalconSwoopError, FalconSwoopWarning
from falcon_swoop.openapi.gen import OpenApiGenerator, OpenApiGeneratorResult, OpenApiGeneratorSettings
from falcon_swoop.openapi.swagger import OpenApiSwaggerUiSettings
from falcon_swoop.operation import operation, operation_doc
from falcon_swoop.operation_spec import OpExample, OpRequestDoc, OpResponseDoc, OpTypeDoc
from falcon_swoop.output import OpOutput
from falcon_swoop.param import header_param, path_param, query_param
from falcon_swoop.resource import SwoopResource

__version__ = "0.1.0"
__all__ = [
    "FalconSwoopError",
    "FalconSwoopConfigError",
    "FalconSwoopWarning",
    "FalconSwoopConfigWarning",
    "SwoopApp",
    "SwoopResource",
    "OpAsgiBinary",
    "OpBinary",
    "header_param",
    "path_param",
    "query_param",
    "OpenApiGenerator",
    "OpenApiGeneratorResult",
    "OpenApiGeneratorSettings",
    "OpenApiSwaggerUiSettings",
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
