from typing import Any

import falcon
import pytest
from pydantic import BaseModel

from falcon_api import ApiBaseResource, operation, operation_doc, header_param, query_param, path_param
from falcon_api.openapi.spec import OpenApiOperation
from falcon_api.operation import HttpMethod
from falcon_api_test.util import SimulatedResource


class BasicInput(BaseModel):
    param1: str


class BasicOutput(BaseModel):
    data: dict[str, Any]


class BasicResource1(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/basic")

    @operation(method="GET")
    def get_something(
        self,
        limit: int = query_param(default=10, ge=1, le=20),
        offset: int = query_param(ge=0),
    ) -> BasicOutput:
        return BasicOutput(data={"limit": limit, "offset": offset})

    @operation(method="POST")
    def post_something(self, basic_input: BasicInput) -> BasicOutput:
        return BasicOutput(data={"param1": basic_input.param1})


class BasicResource2(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/country/{country}/city/{cityId}")

    @operation(method="GET")
    def get_output(
        self,
        country: str = path_param(pattern=r"^[A-Z]{2}$"),
        city_id: int = path_param(alias="cityId", ge=1),
        api_key: str = header_param(default="dummy", alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"country": country, "city": city_id, "api_key": api_key})

    @operation_doc(deprecated=True)
    def on_patch(self, req: falcon.Request, resp: falcon.Response, **params: Any) -> None:
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "patched"

    def on_delete(self, req: falcon.Request, resp: falcon.Response, **params: Any) -> None:
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "deleted"


@pytest.fixture(scope="module")
def resource1() -> SimulatedResource:
    return SimulatedResource(BasicResource1())


@pytest.fixture(scope="module")
def resource2() -> SimulatedResource:
    return SimulatedResource(BasicResource2())


def test_missing_input_raises_400(resource1: SimulatedResource) -> None:
    resp = resource1.simulate_post()
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "resource_fixture_name, methods, exp_allowed_methods",
    [
        ["resource1", {"PUT", "PATCH", "DELETE"}, {"GET", "POST", "OPTIONS"}],
        ["resource2", {"POST", "PUT"}, {"GET", "PATCH", "DELETE", "OPTIONS"}],
    ],
)
def test_unused_operation_raises_405(
    resource_fixture_name: str,
    methods: set[HttpMethod],
    exp_allowed_methods: set[HttpMethod],
    request: pytest.FixtureRequest,
) -> None:
    sim_res: SimulatedResource = request.getfixturevalue(resource_fixture_name)
    for method in methods:
        resp = sim_res.simulate_request(method=method)
        assert resp.status_code == 405, f"Unexpected status code for {method}"
        act_allowed_methods = set(am.strip() for am in resp.headers["allow"].split(","))
        assert act_allowed_methods == exp_allowed_methods, f"Unexpected allow header for {method}"


def test_missing_query_param_raises_400(resource1: SimulatedResource) -> None:
    resp = resource1.simulate_get()
    assert resp.status_code == 400
    resp2 = resource1.simulate_get(params={"offset": 100})
    assert resp2.status_code == 200
    assert resp2.json["data"] == {"limit": 10, "offset": 100}


def test_bad_query_param_raises_400(resource1: SimulatedResource) -> None:
    resp = resource1.simulate_get(params={"offset": 100, "limit": 100})
    assert resp.status_code == 400


def test_bad_path_param_raises_400(resource2: SimulatedResource) -> None:
    route = resource2.resource.api_route
    resp = resource2.simulate_get(path=route.format(country="fr", cityId=1))
    assert resp.status_code == 400
    resp3 = resource2.simulate_get(path=route.format(country="FR", cityId=1))
    assert resp3.status_code == 200
    assert resp3.json["data"]["country"] == "FR"
    assert resp3.json["data"]["city"] == 1


def test_header_parameters_are_case_insensitive(resource2: SimulatedResource) -> None:
    path = resource2.resource.api_route.format(country="FR", cityId=1)
    expected_header_value = "not-dummy"

    resp0 = resource2.simulate_get(path=path)
    assert resp0.status_code == 200
    assert resp0.json["data"]["api_key"] != expected_header_value

    for header in ["X-API-KEY", "x-api-key", "X-ApI-kEy"]:
        resp0 = resource2.simulate_get(path=path, headers={header: expected_header_value})
        assert resp0.status_code == 200
        assert resp0.json["data"]["api_key"] == expected_header_value


def test_operation_decorated_with_docs_only(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_patch(path=resource2.resource.api_route.format(country="ES", cityId=1))
    assert resp.status_code == 200
    assert resp.text == "patched"


def test_operation_not_decorated(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_delete(path=resource2.resource.api_route.format(country="ES", cityId=1))
    assert resp.status_code == 200
    assert resp.text == "deleted"


@pytest.mark.parametrize("resource_fixture_name, exp_op_count", [["resource1", 2], ["resource2", 2]])
def test_openapi_generation(resource_fixture_name: str, exp_op_count: int, request: pytest.FixtureRequest) -> None:
    sim_res: SimulatedResource = request.getfixturevalue(resource_fixture_name)
    result = sim_res.generate_openapi(
        title=sim_res.resource.__class__.__name__,
        version="0.0.1",
    )
    op_count = 0
    for path_item in result.spec.paths.values():
        for v in vars(path_item):
            if isinstance(getattr(path_item, v), OpenApiOperation):
                op_count += 1
    assert op_count == exp_op_count
