# ruff: noqa: D101, D102, D103, D107
import json

from falcon_swoop.binary import OpAsgiBinary, OpBinary
from falcon_swoop.openapi.gen import OpenApiGenerator
from falcon_swoop.openapi.swagger import OpenApiSwaggerUiSettings, build_swagger_ui_html
from falcon_swoop.operation import operation
from falcon_swoop.resource import SwoopResource


class OpenApiBaseResource(SwoopResource):
    def __init__(self, generator: OpenApiGenerator, route: str):
        super().__init__(route)
        self.generator = generator

    def generate_spec_json_bytes(self) -> bytes:
        result = self.generator.generate()
        return json.dumps(result.spec.to_dict()).encode("utf-8")


class OpenApiResource(OpenApiBaseResource):
    @operation(
        method="GET",
        summary="Get OpenAPI specification",
        tags=["meta"],
        response_content_type="application/json",
    )
    def get_open_api_spec(self) -> OpBinary:
        return OpBinary(self.generate_spec_json_bytes())


class OpenApiAsgiResource(OpenApiBaseResource):
    @operation(
        method="GET",
        summary="Get OpenAPI specification",
        tags=["meta"],
        response_content_type="application/json",
    )
    async def get_open_api_spec(self) -> OpAsgiBinary:
        return OpAsgiBinary(self.generate_spec_json_bytes())


class OpenApiSwaggerBaseResource(SwoopResource):
    def __init__(
        self,
        route: str,
        openapi_route: str,
        title: str = "Swagger UI",
        settings: OpenApiSwaggerUiSettings | None = None,
    ):
        super().__init__(route)
        self.openapi_route = openapi_route
        self.title = title
        self.settings = settings

    def generate_swagger_html(self) -> str:
        return build_swagger_ui_html(
            openapi_url_relative=self.openapi_route,
            title=self.title,
            settings=self.settings,
        )


class OpenApiSwaggerResource(OpenApiSwaggerBaseResource):
    @operation(
        method="GET",
        summary="Get OpenAPI swagger",
        tags=["meta"],
        response_content_type="text/html",
    )
    def get_open_api_swagger(self) -> OpBinary:
        return OpBinary(self.generate_swagger_html())


class OpenApiSwaggerAsgiResource(OpenApiSwaggerBaseResource):
    @operation(
        method="GET",
        summary="Get OpenAPI swagger",
        tags=["meta"],
        response_content_type="text/html",
    )
    async def get_open_api_swagger(self) -> OpAsgiBinary:
        return OpAsgiBinary(self.generate_swagger_html())
