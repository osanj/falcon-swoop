from dataclasses import dataclass
from typing import Any, Final, Sequence

from pydantic import BaseModel, create_model

from falcon_swoop import ApiBaseResource
from falcon_swoop.error import FalconSwoopDocGenerationError
from falcon_swoop.openapi.spec import (
    JsonSchema,
    OpenApiComponents,
    OpenApiDocument,
    OpenApiExample,
    OpenApiInfo,
    OpenApiMediaType,
    OpenApiMimeType,
    OpenApiOperation,
    OpenApiPathItem,
    OpenApiReference,
    OpenApiRequestBody,
    OpenApiResponse,
)
from falcon_swoop.operation import (
    HttpMethod,
    OpInfo,
    OpResponseDoc,
    OpRequestDoc,
    OpExample,
    OpType,
    OpTypeDoc,
)


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
            raise FalconSwoopDocGenerationError(f"At least one schema uses a reserved name: {model_name}")
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

    def map_schema(self, op_type: OpType) -> OpenApiReference | JsonSchema | None:
        if op_type is None:
            return None
        if issubclass(op_type, str):
            return {"type": "string"}
        return self.__model_collector.get_reference(op_type)

    def map_example(self, example: OpExample) -> OpenApiExample:
        value: dict[str, Any] | str
        if isinstance(example, BaseModel):
            value = example.model_dump(by_alias=True, mode="json")
        else:
            value = example
        return OpenApiExample(value=value)

    def map_media_type(self, type_doc: OpTypeDoc) -> OpenApiMediaType:
        return OpenApiMediaType(
            schema_=self.map_schema(type_doc.model_type),
            examples={name: self.map_example(example) for name, example in type_doc.examples.items()},
        )

    def map_request_doc(self, rd: OpRequestDoc) -> OpenApiRequestBody | None:
        content = {}
        for mime, resp_type in rd.by_mime.items():
            content[OpenApiMimeType(mime)] = self.map_media_type(resp_type)
        return OpenApiRequestBody(required=rd.required, content=content)

    def map_response_doc(self, rd: OpResponseDoc) -> OpenApiResponse:
        content = {}
        for mime, resp_type in rd.by_mime.items():
            content[OpenApiMimeType(mime)] = self.map_media_type(resp_type)
        return OpenApiResponse(description=rd.description, content=content)

    def map_operation_info(self, op_info: OpInfo) -> OpenApiOperation:
        req_body: OpenApiRequestBody | None = None
        if op_info.request_doc is not None:
            req_body = self.map_request_doc(op_info.request_doc)

        responses = {}
        for status_code, rd in op_info.response_docs.items():
            responses[str(status_code)] = self.map_response_doc(rd)

        return OpenApiOperation(
            operationId=op_info.operation_id,
            summary=op_info.summary,
            description=op_info.description,
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
