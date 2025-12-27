import falcon
import pytest
from pydantic import BaseModel, Field

from falcon_swoop import (
    ApiBaseResource,
    operation,
    operation_doc,
    query_param,
    OpRequestDoc,
    OpResponseDoc,
    OpTypeDoc,
    OpenApiGenerator,
    OpenApiGeneratorResult,
)
from falcon_swoop.openapi.spec import OpenApiReference, OpenApiResponse, OpenApiRequestBody, OpenApiMimeType


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


class DeleteItemsRequest(BaseModel):
    item_ids: list[int] = Field(alias="ids")


class DeleteItemsResponse(BaseModel):
    deleted: list[int]


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

    @operation_doc(
        operation_id="deleteItems",
        request_doc=OpRequestDoc(
            by_mime={
                "application/json": OpTypeDoc.with_default_example(
                    model_type=DeleteItemsRequest,
                    example=DeleteItemsRequest(ids=[1, 2, 3]),
                )
            }
        ),
        response_docs={
            200: OpResponseDoc(
                description="ok",
                by_mime={"application/json": OpTypeDoc.with_default_example(DeleteItemsResponse)},
            ),
            400: OpResponseDoc(
                description="validation-error",
                by_mime={
                    "text/plain": OpTypeDoc.with_default_example(
                        model_type=str,
                        example="missing parameter xyz",
                    )
                },
            ),
            401: OpResponseDoc(description="unauthorized"),
        },
    )
    def on_delete(self, req: falcon.Request, resp: falcon.Response) -> None:
        pass


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
    models: list[type[BaseModel]] = [ItemView, ItemViewsPage, StatsView, RecordItemRequest]
    assert component_schemas.keys() >= {m.__name__ for m in models}

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

    get_items = spec.paths[Items.PATH].get
    assert get_items is not None
    assert get_items.request_body is None
    get_items_200_resp = get_items.responses["200"]
    assert isinstance(get_items_200_resp, OpenApiResponse)
    get_item_200_resp_content = get_items_200_resp.content[OpenApiMimeType.JSON].schema_
    assert isinstance(get_item_200_resp_content, OpenApiReference)
    assert get_item_200_resp_content.ref.startswith(exp_ref)


def test_spec_from_manual_doc(gen_result: OpenApiGeneratorResult) -> None:
    spec = gen_result.spec
    models: list[type[BaseModel]] = [DeleteItemsRequest, DeleteItemsResponse]
    assert spec.components.schemas.keys() >= {m.__name__ for m in models}

    delete_items = spec.paths[Items.PATH].delete
    assert delete_items is not None

    delete_items_req = delete_items.request_body
    assert isinstance(delete_items_req, OpenApiRequestBody)
    assert delete_items_req.content.keys() == {OpenApiMimeType.JSON}
    delete_items_req_content = delete_items_req.content[OpenApiMimeType.JSON]
    assert isinstance(delete_items_req_content.schema_, OpenApiReference)
    assert delete_items_req_content.examples.keys() == {"default"}
    assert delete_items.responses.keys() == {"200", "400", "401"}

    delete_resp_200 = delete_items.responses["200"]
    assert isinstance(delete_resp_200, OpenApiResponse)
    assert delete_resp_200.content[OpenApiMimeType.JSON].schema_ is not None
    assert len(delete_resp_200.content[OpenApiMimeType.JSON].examples) == 0

    delete_resp_400 = delete_items.responses["400"]
    assert isinstance(delete_resp_400, OpenApiResponse)
    assert delete_resp_400.content[OpenApiMimeType.TEXT_PLAIN].schema_ == {"type": "string"}
    assert delete_resp_400.content[OpenApiMimeType.TEXT_PLAIN].examples.keys() == {"default"}

    delete_resp_401 = delete_items.responses["401"]
    assert isinstance(delete_resp_401, OpenApiResponse)
    assert len(delete_resp_401.content) == 0
    assert delete_resp_401.description is not None
