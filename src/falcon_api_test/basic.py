from typing import Any

import pytest
from pydantic import BaseModel

from falcon_api import ApiBaseResource, operation, header_param, query_param, path_param
from falcon_api_test.util import SimulatedResource


class BasicInput(BaseModel):
    param1: str


class BasicOutput(BaseModel):
    data: dict[str, Any]


class BasicResource(ApiBaseResource):

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


class BasicResourceWithPath(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/country/{country}/city/{cityId}")

    @operation(method="GET")
    def get_post(
        self,
        country: str = path_param(pattern=r"^[A-Z]{2}$"),
        city_id: int = path_param(alias="cityId", ge=1),
        api_key: str = header_param(default="dummy", alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"country": country, "city": city_id, "api_key": api_key})


@pytest.fixture(scope="module")
def resource() -> SimulatedResource:
    return SimulatedResource(BasicResource())


@pytest.fixture(scope="module")
def resource_with_path() -> SimulatedResource:
    return SimulatedResource(BasicResourceWithPath())


def test_missing_input_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_post()
    assert resp.status_code == 400


def test_unused_operation_raises_405(resource: SimulatedResource) -> None:
    for method in ["PUT", "PATCH", "DELETE"]:
        resp = resource.simulate_request(method=method)  # type: ignore[arg-type]
        assert resp.status_code == 405, f"Unexpected status code for {method}"
        assert resp.headers["allow"] == "GET, POST", f"Unexpected allow header for {method}"


def test_missing_query_param_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_get()
    assert resp.status_code == 400
    resp2 = resource.simulate_get(params={"offset": 100})
    assert resp2.status_code == 200
    assert resp2.json["data"] == {"limit": 10, "offset": 100}


def test_bad_query_param_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_get(params={"offset": 100, "limit": 100})
    assert resp.status_code == 400


def test_bad_path_param_raises_400(resource_with_path: SimulatedResource) -> None:
    route = resource_with_path.resource.api_route
    resp = resource_with_path.simulate_get(path=route.format(country="fr", cityId=1))
    assert resp.status_code == 400
    resp3 = resource_with_path.simulate_get(path=route.format(country="FR", cityId=1))
    assert resp3.status_code == 200
    assert resp3.json["data"]["country"] == "FR"
    assert resp3.json["data"]["city"] == 1


def test_header_parameters_are_case_insensitive(resource_with_path: SimulatedResource) -> None:
    path = resource_with_path.resource.api_route.format(country="FR", cityId=1)
    expected_header_value = "not-dummy"

    resp0 = resource_with_path.simulate_get(path=path)
    assert resp0.status_code == 200
    assert resp0.json["data"]["api_key"] != expected_header_value

    for header in ["X-API-KEY", "x-api-key", "X-ApI-kEy"]:
        resp0 = resource_with_path.simulate_get(path=path, headers={header: expected_header_value})
        assert resp0.status_code == 200
        assert resp0.json["data"]["api_key"] == expected_header_value


@pytest.mark.parametrize("resource_fixture_name", ["resource", "resource_with_path"])
def test_openapi_generation(resource_fixture_name: str, request: pytest.FixtureRequest) -> None:
    sim_res: SimulatedResource = request.getfixturevalue(resource_fixture_name)
    sim_res.generate_openapi(
        title=sim_res.resource.__class__.__name__,
        version="0.0.1",
    )
