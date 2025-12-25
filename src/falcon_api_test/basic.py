import pytest
from pydantic import BaseModel

from falcon_api import ApiBaseResource, operation, ApiQueryParam
from falcon_api_test.util import SimulatedResource


class BasicInput(BaseModel):
    param1: str


class BasicOutput(BaseModel):
    param1: str


class BasicResource(ApiBaseResource):

    def __init__(self):
        super().__init__("/basic")

    @operation(method="GET")
    def basic_get(
        self,
        limit: int = ApiQueryParam(default=10, ge=1, le=20),
        offset: int = ApiQueryParam(ge=0),
    ) -> BasicOutput:
        return BasicOutput(param1=f"limit={limit}&offset={offset}")

    @operation(method="POST")
    def basic_post(self, basic_input: BasicInput) -> BasicOutput:
        return BasicOutput(param1=basic_input.param1)


@pytest.fixture(scope="module")
def resource() -> SimulatedResource:
    return SimulatedResource(BasicResource())


def test_missing_input_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_post()
    assert resp.status_code == 400


def test_unused_operation_raises_405(resource: SimulatedResource) -> None:
    for method in ["PUT", "PATCH", "DELETE"]:
        resp = resource.simulate_request(method=method)
        assert resp.status_code == 405, f"Unexpected status code for {method}"
        assert resp.headers["allow"] == "GET, POST", f"Unexpected allow header for {method}"


def test_missing_query_param_raises_400(resource: SimulatedResource) -> None:
    resp = resource.simulate_get()
    assert resp.status_code == 400
    resp2 = resource.simulate_get(params={"offset": 100})
    assert resp2.status_code == 200
    assert resp2.text == "limit=10&offset=100"


def test_bad_query_param_raises_400(resource: SimulatedResource) -> None:
    resp2 = resource.simulate_get(params={"offset": 100, "limit": 100})
    assert resp2.status_code == 400
