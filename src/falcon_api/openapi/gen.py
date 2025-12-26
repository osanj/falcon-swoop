from dataclasses import dataclass
from typing import Final, Sequence

from pydantic import BaseModel, create_model

from falcon_api import ApiBaseResource
from falcon_api.error import FalconApiDocGenerationError
from falcon_api.openapi.spec import (
    JsonSchema,
    OpenApiComponents,
    OpenApiDocument,
    OpenApiInfo,
    OpenApiMediaType,
    OpenApiMimeType,
    OpenApiPathItem,
    OpenApiOperation,
    OpenApiReference,
    OpenApiRequestBody,
    OpenApiResponse,
)
from falcon_api.operation import HttpMethod, OperationInfo


@dataclass
class OpenApiGeneratorSettings:
    pass


@dataclass
class OpenApiGeneratorResult:
    spec: OpenApiDocument


class OpenApiModelCollector:
    REF_TEMPLATE: Final[str] = "#/components/schemas/{model}"

    def __init__(self) -> None:
        self.__models: set[type[BaseModel]] = set()

    def get_schemas(self) -> dict[str, JsonSchema]:
        """
        Generate a temporary model that has one parameter with each given model,
        pydantic will then generate the schemas for all parameters into $def and taking care of duplication etc.
        """
        model_name = "SchemaContainerForJsonSchemaGeneration"
        if model_name in [m.__name__ for m in self.__models]:
            raise FalconApiDocGenerationError(f"At least one schema uses a reserved name: {model_name}")
        model_params = {f"param{i}": (m, ...) for i, m in enumerate(self.__models)}
        model = create_model(model_name, **model_params)  # type: ignore
        model_schema = model.model_json_schema(by_alias=True, ref_template=self.REF_TEMPLATE)
        schemas: dict[str, JsonSchema] = model_schema.get("$defs", {})
        return schemas

    def get_reference(self, model_type: type[BaseModel]) -> OpenApiReference:
        ref_url = self.REF_TEMPLATE.format(model=model_type.__name__)
        self.__models.add(model_type)
        return OpenApiReference(ref=ref_url)


class OpenApiGenerator:

    def __init__(
        self,
        resources: Sequence[ApiBaseResource],
        title: str,
        version: str,
        summary: str | None = None,
        description: str | None = None,
        settings: OpenApiGeneratorSettings | None = None,
    ) -> None:
        self.resources = resources
        self.settings = settings or OpenApiGeneratorSettings()
        self.__model_collector = OpenApiModelCollector()
        self.info = OpenApiInfo(
            title=title,
            version=version,
            summary=summary,
            description=description,
        )

    def map_operation_info(self, op_info: OperationInfo) -> OpenApiOperation:
        req_body: OpenApiRequestBody | None = None
        if op_info.func_input is not None:
            req_body = OpenApiRequestBody(
                required=True,
                content={
                    OpenApiMimeType(mime): OpenApiMediaType(
                        schema_=self.__model_collector.get_reference(op_info.func_input.model)
                    )
                    for mime in op_info.accept
                },
            )

        responses = {}
        if op_info.func_output_model is not None:
            responses["200"] = OpenApiResponse(
                description="success",
                content={
                    OpenApiMimeType.JSON: OpenApiMediaType(
                        schema_=self.__model_collector.get_reference(op_info.func_output_model)
                    )
                },
            )

        return OpenApiOperation(
            operationId=op_info.operation_id,
            summary=op_info.func.__doc__,
            tags=op_info.tags,
            deprecated=op_info.deprecated,
            requestBody=req_body,
            responses=responses,
        )

    def map_api_resource(self, resource: ApiBaseResource) -> OpenApiPathItem:
        operations: dict[HttpMethod, OpenApiOperation] = {}
        for op_info in resource.api_ops():
            operations[op_info.method] = self.map_operation_info(op_info)
        return OpenApiPathItem(
            summary=resource.__doc__,
            **{method.lower(): op for method, op in operations.items()},
        )

    def generate(self) -> OpenApiGeneratorResult:
        paths: dict[str, OpenApiPathItem] = {}
        for r in self.resources:
            paths[r.api_route.plain] = self.map_api_resource(r)

        schemas = self.__model_collector.get_schemas()
        # TODO: params
        # TODO: security_schemas
        components = OpenApiComponents(schemas=schemas)

        spec = OpenApiDocument(
            info=self.info,
            paths=paths,
            components=components,
        )
        return OpenApiGeneratorResult(spec=spec)
