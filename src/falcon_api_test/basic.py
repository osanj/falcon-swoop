import pytest
from pydantic import BaseModel

from falcon_api import ApiBaseResource, operation, query_param, path_param
from falcon_api_test.util import SimulatedResource


class BasicInput(BaseModel):
    param1: str


class BasicOutput(BaseModel):
    param1: str


class BasicResource(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/basic")

    @operation(method="GET")
    def get_something(
        self,
        limit: int = query_param(default=10, ge=1, le=20),
        offset: int = query_param(ge=0),
    ) -> BasicOutput:
        return BasicOutput(param1=f"limit={limit}&offset={offset}")

    @operation(method="POST")
    def post_something(self, basic_input: BasicInput) -> BasicOutput:
        return BasicOutput(param1=basic_input.param1)


class BasicResourceWithPath(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/country/{country}/city/{cityId}")

    @operation(method="GET")
    def get_post(
        self,
        country: str = path_param(pattern=r"^[A-Z]{2}$"),
        city_id: int = path_param(alias="cityId", ge=1),
    ) -> BasicOutput:
        return BasicOutput(param1=f"country={country}&city={city_id}")


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
    assert resp2.json["param1"] == "limit=10&offset=100"


def test_bad_query_param_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_get(params={"offset": 100, "limit": 100})
    assert resp.status_code == 400


def test_bad_path_param_raises_400(resource_with_path: SimulatedResource) -> None:
    route = resource_with_path.resource.route
    resp = resource_with_path.simulate_get(path=route.format(country="fr", cityId=1))
    assert resp.status_code == 400
    resp3 = resource_with_path.simulate_get(path=route.format(country="FR", cityId=1))
    assert resp3.status_code == 200
    assert resp3.json["param1"] == "country=FR&city=1"
