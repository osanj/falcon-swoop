# ruff: noqa: D400
import re
from enum import Enum, unique
from typing import Any, Literal

from typing_extensions import Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

JsonSchema = dict[str, Any]


def _check_content_types(content_types: list[str]) -> None:
    for ct in content_types:
        if not (ct.count("/") == 1 and len(ct) >= 3):
            raise ValueError(f"Invalid content type {ct}")


@unique
class OpenApiParameterType(str, Enum):  # noqa: D101
    QUERY = "query"
    HEADER = "header"
    PATH = "path"
    COOKIE = "cookie"


class OpenApiSpecModel(BaseModel):
    """Base model for OpenAPI spec representation. Subclasses may be incomplete, check links to spec."""

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self, mode: Literal["json", "python"] = "json") -> dict[Any, str]:
        """Export OpenAPI spec into a dictionary.

        Importantly, all values set to ``None`` will be removed from the output.

        :param mode: corresponding to the argument for model_dump from pydantic, ``json`` will lead to basic datatypes
            which is good for serialization, with ``python`` string enums may "survive" as enums instead of classes.
        """
        return self.model_dump(mode=mode, by_alias=True, exclude_none=True)


class OpenApiExternalDocumentation(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#external-documentation-object"""

    description: str | None = None
    url: AnyHttpUrl


class OpenApiReference(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#reference-object"""

    ref: str = Field(alias="$ref")
    summary: str | None = None
    description: str | None = None


class OpenApiParameter(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#parameter-object"""

    name: str
    in_: OpenApiParameterType = Field(alias="in")
    description: str | None = None
    required: bool = False
    deprecated: bool = False
    # allow_empty_value: bool = Field(default=False, alias="allowEmptyValue")  # likely to be removed
    schema_: JsonSchema = Field(alias="schema")
    # content is not supported for now

    @model_validator(mode="after")
    def check_required_for_path(self) -> Self:
        """https://spec.openapis.org/oas/v3.1.0#fixed-fields-9"""
        if self.in_ == OpenApiParameterType.PATH and not self.required:
            raise ValueError("Path parameters must be required")
        return self


class OpenApiApiKeySecurityScheme(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#security-scheme-object"""

    type: Literal["apiKey"] = "apiKey"
    description: str | None = None
    name: str
    in_: Literal[OpenApiParameterType.HEADER, OpenApiParameterType.QUERY, OpenApiParameterType.COOKIE] = Field(
        alias="in"
    )


class OpenApiExample(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#example-object"""

    summary: str | None = None
    description: str | None = None
    value: str | dict[str, Any] | None = None
    external_value: str | None = Field(default=None, alias="externalValue")

    @model_validator(mode="after")
    def _ensure_values_are_mutually_exclusive(self) -> Self:
        if (self.value is None) == (self.external_value is None):
            raise ValueError("Either value or external_value must be specified, they can't be both present or absent")
        return self


class OpenApiMediaType(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#media-type-object"""

    schema_: OpenApiReference | JsonSchema | None = Field(default=None, alias="schema")
    examples: dict[str, OpenApiExample] = Field(default_factory=dict)


class OpenApiRequestBody(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#request-body-object"""

    description: str | None = None
    content: dict[str, OpenApiMediaType]
    required: bool = False

    @model_validator(mode="after")
    def _ensure_valid_content_types(self) -> Self:
        _check_content_types(list(self.content.keys()))
        return self


class OpenApiResponse(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#response-object"""

    description: str
    content: dict[str, OpenApiMediaType]

    @model_validator(mode="after")
    def _ensure_valid_content_types(self) -> Self:
        _check_content_types(list(self.content.keys()))
        return self


class OpenApiOperation(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#operation-object"""

    tags: list[str] = []
    summary: str | None = None
    description: str | None = None
    external_docs: OpenApiExternalDocumentation | None = Field(default=None, alias="externalDocs")
    operation_id: str | None = Field(default=None, alias="operationId")
    parameters: list[OpenApiParameter | OpenApiReference] = Field(default_factory=list)
    request_body: OpenApiRequestBody | OpenApiReference | None = Field(default=None, alias="requestBody")
    responses: dict[str, OpenApiResponse | OpenApiReference]
    security: list[dict[str, list[str]]] | None = None  # emtpy array can be passed to remove top level requirements
    deprecated: bool = False

    @field_validator("responses")
    @classmethod
    def response_keys_are_http_status_codes(cls, responses: dict[str, Any]) -> dict[str, Any]:
        """https://spec.openapis.org/oas/v3.1.0#responses-object"""
        for status_code in responses:
            if not (status_code == "default" or re.fullmatch(r"[2-5]\d\d", status_code)):
                raise ValueError(f"Response code {status_code} is not valid")
        return responses


class OpenApiPathItem(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#path-item-object"""

    summary: str | None = None
    description: str | None = None
    get: OpenApiOperation | None = None
    put: OpenApiOperation | None = None
    post: OpenApiOperation | None = None
    delete: OpenApiOperation | None = None
    options: OpenApiOperation | None = None
    head: OpenApiOperation | None = None
    patch: OpenApiOperation | None = None
    trace: OpenApiOperation | None = None
    parameters: list[OpenApiParameter | OpenApiReference] = []


class OpenApiTag(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#tag-object"""

    name: str
    description: str | None = None
    external_docs: OpenApiExternalDocumentation | None = Field(default=None, alias="externalDocs")


class OpenApiInfo(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#info-object"""

    title: str
    summary: str | None = None
    description: str | None = None
    version: str


class OpenApiComponents(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#components-object"""

    schemas: dict[str, JsonSchema] = Field(default_factory=dict)
    parameters: dict[str, OpenApiParameter | OpenApiReference] = Field(default_factory=dict)
    security_schemes: dict[str, OpenApiApiKeySecurityScheme] = Field(alias="securitySchemes", default_factory=dict)


class OpenApiDocument(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#openapi-object"""

    # not complete!

    openapi: str = "3.1.0"
    info: OpenApiInfo
    paths: dict[str, OpenApiPathItem] = {}
    components: OpenApiComponents = Field(default_factory=OpenApiComponents)
    security: list[dict[str, list[str]]] | None = None
    tags: list[OpenApiTag] = []
    external_docs: OpenApiExternalDocumentation | None = Field(default=None, alias="externalDocs")

    @field_validator("paths")
    @classmethod
    def paths_need_to_start_with_slash(cls, paths: dict[str, Any]) -> dict[str, Any]:
        """https://spec.openapis.org/oas/v3.1.0#paths-object"""
        for path in paths:
            if not path.startswith("/"):
                raise ValueError(f"Path {path} does not start with '/'")
        return paths
