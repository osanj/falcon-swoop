import pytest
from pydantic import BaseModel

from falcon_api import (
    ApiBaseResource,
    operation,
    query_param,
    OpenApiGenerator,
    OpenApiGeneratorResult,
)
from falcon_api.openapi.spec import OpenApiReference, OpenApiResponse, OpenApiRequestBody, OpenApiMimeType


class RecordItemRequest(BaseModel):
    name: str
    value: int


class StatsView(BaseModel):
    count: int
    min_value: int
    max_value: int


class ItemView(BaseModel):
    id: int
    name: str
    stats: StatsView


class ItemViewsPage(BaseModel):
    items: list[ItemView]
    offset: int
    overall_count: int


class Item(ApiBaseResource):
    PATH = "/item"

    def __init__(self) -> None:
        super().__init__(self.PATH)

    @operation(method="GET")
    def get_item_by_id(
        self,
        item_id: int = query_param(ge=1),
    ) -> ItemView:
        return ItemView(
            id=item_id,
            name="name",
            stats=StatsView(count=1, min_value=1, max_value=1),
        )

    @operation(method="POST")
    def record_item(self, req: RecordItemRequest) -> None:
        pass


class Items(ApiBaseResource):
    PATH = "/items"

    def __init__(self) -> None:
        super().__init__(self.PATH)

    @operation(method="GET")
    def get_items(
        self,
        offset: int = query_param(default=0, ge=0),
        limit: int = query_param(default=20, ge=1, le=50),
    ) -> ItemViewsPage:
        return ItemViewsPage(items=[], offset=offset, overall_count=100)


@pytest.fixture(scope="module")
def gen_result() -> OpenApiGeneratorResult:
    generator = OpenApiGenerator(
        resources=[Item(), Items()],
        title="Item API",
        version="0.0.1",
    )
    return generator.generate()


SCHEMA_PROPS = "properties"
SCHEMA_REF = "$ref"


def test_usage_of_model_references(gen_result: OpenApiGeneratorResult) -> None:
    spec = gen_result.spec
    component_schemas = spec.components.schemas
    all_models = [ItemView, ItemViewsPage, StatsView, RecordItemRequest]
    assert component_schemas.keys() == {m.__name__ for m in all_models}

    exp_ref = "#/components/schemas"
    assert component_schemas[ItemView.__name__][SCHEMA_PROPS]["stats"][SCHEMA_REF].startswith(exp_ref)
    assert component_schemas[ItemViewsPage.__name__][SCHEMA_PROPS]["items"]["type"] == "array"
    assert component_schemas[ItemViewsPage.__name__][SCHEMA_PROPS]["items"]["items"][SCHEMA_REF].startswith(exp_ref)

    get_item = spec.paths[Item.PATH].get
    assert get_item is not None
    get_item_200_resp = get_item.responses["200"]
    assert isinstance(get_item_200_resp, OpenApiResponse)
    get_item_200_resp_content = get_item_200_resp.content[OpenApiMimeType.JSON].schema_
    assert isinstance(get_item_200_resp_content, OpenApiReference)
    assert get_item_200_resp_content.ref.startswith(exp_ref)

    post_item = spec.paths[Item.PATH].post
    assert post_item is not None
    post_item_req = post_item.request_body
    assert isinstance(post_item_req, OpenApiRequestBody)
    post_item_req_content = post_item_req.content[OpenApiMimeType.JSON].schema_
    assert isinstance(post_item_req_content, OpenApiReference)
    assert post_item_req_content.ref.startswith(exp_ref)
