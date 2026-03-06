from typing import Any, Sequence, Set

import falcon
import pytest
from pydantic import BaseModel, Field

from falcon_swoop import (
    OpBinary,
    OpenApiGenerator,
    OpRequestDoc,
    OpResponseDoc,
    OpTypeDoc,
    SwoopResource,
    header_param,
    operation,
    operation_doc,
    path_param,
    query_param,
)
from falcon_swoop.openapi.spec import (
    OpenApiDocument,
    OpenApiParameter,
    OpenApiParameterType,
    OpenApiReference,
    OpenApiRequestBody,
    OpenApiResponse,
)

CT_JSON = "application/json"
CT_TEXT = "text/plain"


class RecordItemRequest(BaseModel):
    name: str
    value: int


class StatsView(BaseModel):
    count: int
    min_value: int
    max_value: int


class PostView(BaseModel):
    id: int
    content: str


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


class Item(SwoopResource):
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

    @operation(method="PATCH")
    def update_item(self, req: RecordItemRequest | None, item_id: int = query_param(ge=1)) -> None:
        pass


class Items(SwoopResource):
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


class Post(SwoopResource):
    PATH = "/posts/{postId}"

    def __init__(self) -> None:
        super().__init__(self.PATH)

    @operation(method="GET", tags=["posts"])
    def get_post(
        self,
        post_id: int = path_param(alias="postId"),
    ) -> PostView:
        return PostView(id=post_id, content="lorem ipsum")

    @operation(method="DELETE", tags=["posts"])
    def delete_post(
        self, post_id: int = path_param(alias="postId"), admin_key: str = header_param(alias="X-ADMIN-KEY")
    ) -> None:
        pass


class PostMedia(SwoopResource):
    PATH = "/posts/{postId}/media"

    def __init__(self) -> None:
        super().__init__(self.PATH)

    @operation(
        method="PUT",
        tags=["posts"],
        accept=["image/*", "application/pdf"],
        default_status=201,
        response_content_type="text/plain",
        response_example="id=123",
        more_response_docs={400: OpResponseDoc("bad_bytes")},
    )
    def add_media(
        self,
        media: OpBinary,
        post_id: int = path_param(alias="postId"),
    ) -> OpBinary:
        return OpBinary("id=999")


@pytest.fixture(scope="module")
def gen() -> OpenApiGenerator:
    return OpenApiGenerator(
        resources=[Item(), Items(), Post(), PostMedia()],
        title="Item API",
        version="0.0.1",
    )


@pytest.fixture(scope="module")
def spec(gen: OpenApiGenerator) -> OpenApiDocument:
    return gen.generate().spec


SCHEMA_PROPS = "properties"
SCHEMA_REF = "$ref"


def test_usage_of_model_references(spec: OpenApiDocument) -> None:
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
    get_item_200_resp_content = get_item_200_resp.content[CT_JSON].schema_
    assert isinstance(get_item_200_resp_content, OpenApiReference)
    assert get_item_200_resp_content.ref.startswith(exp_ref)

    post_item = spec.paths[Item.PATH].post
    assert post_item is not None
    post_item_req = post_item.request_body
    assert isinstance(post_item_req, OpenApiRequestBody)
    post_item_req_content = post_item_req.content[CT_JSON].schema_
    assert isinstance(post_item_req_content, OpenApiReference)
    assert post_item_req_content.ref.startswith(exp_ref)

    get_items = spec.paths[Items.PATH].get
    assert get_items is not None
    assert get_items.request_body is None
    get_items_200_resp = get_items.responses["200"]
    assert isinstance(get_items_200_resp, OpenApiResponse)
    get_item_200_resp_content = get_items_200_resp.content[CT_JSON].schema_
    assert isinstance(get_item_200_resp_content, OpenApiReference)
    assert get_item_200_resp_content.ref.startswith(exp_ref)


def test_optional_input_marked_accordingly(spec: OpenApiDocument) -> None:
    post = spec.paths[Item.PATH].post
    assert post is not None
    assert isinstance(post.request_body, OpenApiRequestBody)
    assert post.request_body.required

    patch = spec.paths[Item.PATH].patch
    assert patch is not None
    assert isinstance(patch.request_body, OpenApiRequestBody)
    assert not patch.request_body.required


def test_spec_from_manual_doc(spec: OpenApiDocument) -> None:
    models: list[type[BaseModel]] = [DeleteItemsRequest, DeleteItemsResponse]
    assert spec.components.schemas.keys() >= {m.__name__ for m in models}

    delete_items = spec.paths[Items.PATH].delete
    assert delete_items is not None

    delete_items_req = delete_items.request_body
    assert isinstance(delete_items_req, OpenApiRequestBody)
    assert delete_items_req.content.keys() == {CT_JSON}
    delete_items_req_content = delete_items_req.content[CT_JSON]
    assert isinstance(delete_items_req_content.schema_, OpenApiReference)
    assert delete_items_req_content.examples.keys() == {"default"}
    assert delete_items.responses.keys() == {"200", "400", "401"}

    delete_resp_200 = delete_items.responses["200"]
    assert isinstance(delete_resp_200, OpenApiResponse)
    assert delete_resp_200.content[CT_JSON].schema_ is not None
    assert len(delete_resp_200.content[CT_JSON].examples) == 0

    delete_resp_400 = delete_items.responses["400"]
    assert isinstance(delete_resp_400, OpenApiResponse)
    assert delete_resp_400.content[CT_TEXT].schema_ == {"type": "string"}
    assert delete_resp_400.content[CT_TEXT].examples.keys() == {"default"}

    delete_resp_401 = delete_items.responses["401"]
    assert isinstance(delete_resp_401, OpenApiResponse)
    assert len(delete_resp_401.content) == 0
    assert delete_resp_401.description is not None


def lookup_and_check_params(
    spec: OpenApiDocument,
    params: Sequence[OpenApiParameter | OpenApiReference],
    params_exp: Sequence[tuple[str, OpenApiParameterType]],
) -> None:
    params_out: list[OpenApiParameter] = []
    for p in params:
        if isinstance(p, OpenApiParameter):
            params_out.append(p)
        else:
            _, param_ref = p.ref.rsplit("/", maxsplit=1)
            p2 = spec.components.parameters[param_ref]
            assert isinstance(p2, OpenApiParameter)
            params_out.append(p2)

    params_act = [(p.name, p.in_) for p in params_out]
    assert set(params_act) == set(params_exp)


def test_param_generation(spec: OpenApiDocument) -> None:
    params_act = [(p.name, p.in_) for p in spec.components.parameters.values() if isinstance(p, OpenApiParameter)]
    params_exp = [
        ("item_id", OpenApiParameterType.QUERY),
        ("offset", OpenApiParameterType.QUERY),
        ("limit", OpenApiParameterType.QUERY),
        ("postId", OpenApiParameterType.PATH),
        ("X-ADMIN-KEY", OpenApiParameterType.HEADER),
    ]
    assert set(params_act) == set(params_exp)

    lookup_and_check_params(
        spec=spec,
        params=spec.paths[Item.PATH].get.parameters,  # type: ignore
        params_exp=[("item_id", OpenApiParameterType.QUERY)],
    )
    lookup_and_check_params(
        spec=spec,
        params=spec.paths[Item.PATH].patch.parameters,  # type: ignore
        params_exp=[("item_id", OpenApiParameterType.QUERY)],
    )
    lookup_and_check_params(
        spec=spec,
        params=spec.paths[Items.PATH].get.parameters,  # type: ignore
        params_exp=[
            ("offset", OpenApiParameterType.QUERY),
            ("limit", OpenApiParameterType.QUERY),
        ],
    )
    lookup_and_check_params(
        spec=spec,
        params=spec.paths[Post.PATH].get.parameters,  # type: ignore
        params_exp=[
            ("postId", OpenApiParameterType.PATH),
        ],
    )
    lookup_and_check_params(
        spec=spec,
        params=spec.paths[Post.PATH].delete.parameters,  # type: ignore
        params_exp=[
            ("postId", OpenApiParameterType.PATH),
            ("X-ADMIN-KEY", OpenApiParameterType.HEADER),
        ],
    )


def test_param_reuse(gen: OpenApiGenerator) -> None:
    assert gen.settings.reuse_parameters_if_possible
    spec1 = gen.generate().spec

    gen.settings.reuse_parameters_if_possible = False
    spec2 = gen.generate().spec
    assert len(spec1.components.parameters) < len(spec2.components.parameters)


def test_doc_gen_for_binary_op_data(spec: OpenApiDocument) -> None:
    upload_op = spec.paths[PostMedia.PATH].put
    assert upload_op is not None

    binary_schema = {"type": "string", "format": "binary"}

    assert isinstance(upload_op.request_body, OpenApiRequestBody)
    assert upload_op.request_body.required
    assert upload_op.request_body.content.keys() == {"image/*", "application/pdf"}
    assert upload_op.request_body.content["image/*"].schema_ == binary_schema
    assert upload_op.request_body.content["application/pdf"].schema_ == binary_schema

    assert upload_op.responses.keys() == {"201", "400"}
    assert isinstance(upload_op.responses["201"], OpenApiResponse)
    assert upload_op.responses["201"].description == "ok"
    assert upload_op.responses["201"].content["text/plain"].schema_ == binary_schema
    assert upload_op.responses["400"].description == "bad_bytes"


def get_all_keys(data: dict[str, Any], keys_found: Set[str] | None = None) -> Set[str]:
    if keys_found is None:
        keys_found = set()

    for key, value in data.items():
        keys_found.add(key)

        if isinstance(value, dict):
            get_all_keys(value, keys_found)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    get_all_keys(item, keys_found)

    return keys_found


def test_title_generation_config(gen: OpenApiGenerator) -> None:
    gen.settings.suppress_title_in_param_schemas = True
    gen.settings.suppress_title_in_object_schemas = False
    comps1 = gen.generate().spec.components
    param_schemas_wo_title = {k: p.schema_ for k, p in comps1.parameters.items() if isinstance(p, OpenApiParameter)}
    schemas_wi_title = comps1.schemas
    assert "title" not in get_all_keys(param_schemas_wo_title)
    assert "title" in get_all_keys(schemas_wi_title)

    gen.settings.suppress_title_in_param_schemas = False
    gen.settings.suppress_title_in_object_schemas = True
    comps2 = gen.generate().spec.components
    schemas_wo_title = comps2.schemas
    param_schemas_wi_title = {k: p.schema_ for k, p in comps2.parameters.items() if isinstance(p, OpenApiParameter)}
    assert "title" in get_all_keys(param_schemas_wi_title)
    assert "title" not in get_all_keys(schemas_wo_title)
