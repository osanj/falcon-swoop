import re
from enum import Enum, unique
from typing import Any, Dict, List, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

JsonSchema = Dict[str, Any]


@unique
class OpenApiMimeType(str, Enum):
    ANY = "*/*"
    OCTET_STREAM = "application/octet-stream"
    JSON = "application/json"
    YAML = "application/yaml"
    XML = "application/xml"
    PDF = "application/pdf"
    PNG = "image/png"
    JPEG = "image/jpeg"
    MP4 = "video/mp4"
    WEBM_VIDEO = "video/webm"
    MPEG_AUDIO = "audio/mpeg"  # mp3
    MP4_AUDIO = "audio/mp4"  # m4a
    WAV = "audio/wav"
    WEBM_AUDIO = "audio/webm"
    HTML = "text/html"
    TEXT_PLAIN = "text/plain"
    MULTIPART_FORM_DATA = "multipart/form-data"
    # MULTIPART_MIXED = "multipart/mixed"  # When to use?


@unique
class OpenApiParameterType(str, Enum):
    QUERY = "query"
    HEADER = "header"
    PATH = "path"
    COOKIE = "cookie"


class OpenApiSpecModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


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
    def check_required_for_path(self) -> "OpenApiParameter":
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


class OpenApiMediaType(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#media-type-object"""

    schema_: OpenApiReference | JsonSchema | None = Field(default=None, alias="schema")


class OpenApiRequestBody(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#request-body-object"""

    description: str | None = None
    content: Dict[OpenApiMimeType, OpenApiMediaType]
    required: bool = False


class OpenApiResponse(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#response-object"""

    description: str
    content: Dict[OpenApiMimeType, OpenApiMediaType]


class OpenApiOperation(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#operation-object"""

    tags: List[str] = []
    summary: str | None = None
    description: str | None = None
    external_docs: OpenApiExternalDocumentation | None = Field(default=None, alias="externalDocs")
    operation_id: str | None = Field(default=None, alias="operationId")
    parameters: List[OpenApiParameter | OpenApiReference] = Field(default_factory=list)
    request_body: OpenApiRequestBody | OpenApiReference | None = Field(default=None, alias="requestBody")
    responses: Dict[str, OpenApiResponse | OpenApiReference]
    security: List[Dict[str, List[str]]] | None = None  # emtpy array can be passed to remove top level requirements
    deprecated: bool = False

    @field_validator("responses")
    @classmethod
    def response_keys_are_http_status_codes(cls, responses: Dict[str, Any]) -> Dict[str, Any]:
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
    parameters: List[OpenApiParameter | OpenApiReference] = []


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

    schemas: Dict[str, JsonSchema] = Field(default_factory=dict)
    parameters: Dict[str, OpenApiParameter | OpenApiReference] = Field(default_factory=dict)
    security_schemes: Dict[str, OpenApiApiKeySecurityScheme] = Field(alias="securitySchemes", default_factory=dict)


class OpenApiDocument(OpenApiSpecModel):
    """https://spec.openapis.org/oas/v3.1.0#openapi-object"""

    # not complete!

    openapi: str = "3.1.0"
    info: OpenApiInfo
    paths: Dict[str, OpenApiPathItem] = {}
    components: OpenApiComponents = Field(default_factory=OpenApiComponents)
    security: List[Dict[str, List[str]]] | None = None
    tags: List[OpenApiTag] = []
    external_docs: OpenApiExternalDocumentation | None = Field(default=None, alias="externalDocs")

    @field_validator("paths")
    @classmethod
    def paths_need_to_start_with_slash(cls, paths: Dict[str, Any]) -> Dict[str, Any]:
        """https://spec.openapis.org/oas/v3.1.0#paths-object"""
        for path in paths:
            if not path.startswith("/"):
                raise ValueError(f"Path {path} does not start with '/'")
        return paths
