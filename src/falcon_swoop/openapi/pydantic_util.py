# ruff: noqa: D101, D102, D103
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaValue


class GenerateJsonSchemaNoTitles(GenerateJsonSchema):
    def field_title_should_be_set(self, schema: Any) -> bool:
        return False


def model_json_schema(
    model_type: type[BaseModel],
    by_alias: bool = True,
    ref_template: str = DEFAULT_REF_TEMPLATE,
    suppress_title: bool = False,
) -> JsonSchemaValue:
    schema_generator = GenerateJsonSchemaNoTitles if suppress_title else GenerateJsonSchema
    return model_type.model_json_schema(
        by_alias=by_alias,
        ref_template=ref_template,
        schema_generator=schema_generator,
    )
