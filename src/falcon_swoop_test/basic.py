from typing import Any

import falcon
import pytest
from pydantic import BaseModel

from falcon_swoop import ApiBaseResource, operation, operation_doc, header_param, query_param, path_param
from falcon_swoop.openapi.spec import OpenApiOperation
from falcon_swoop.operation import HttpMethod
from falcon_swoop_test.util import SimulatedResource


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


country_param = path_param(pattern=r"^[A-Z]{2}$")
city_id_param = path_param(alias="cityId", ge=1)


class BasicResource2(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/country/{country}/city/{cityId}")

    @operation(method="GET")
    def get_city_data(
        self,
        country: str = country_param,
        city_id: int = city_id_param,
        api_key: str = header_param(default="dummy", alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"country": country, "city": city_id, "api_key": api_key})

    @operation(method="PUT")
    def put_city_data(
        self,
        req: BasicInput | None,
        country: str = country_param,
        city_id: int = city_id_param,
        tag: str | None = query_param(),
        api_key: str | None = header_param(alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"tag": tag, "api_key": api_key, "param1": None if req is None else req.param1})

    @operation_doc(operation_id="updateCityData", deprecated=True)
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
    resp = resource1.simulate_post(json_model=BasicInput(param1="test"))
    assert resp.status_code == 200
    assert resp.json["data"]["param1"] == "test"

    resp_missing = resource1.simulate_post()
    assert resp_missing.status_code == 400


@pytest.mark.parametrize(
    "resource_fixture_name, methods, exp_allowed_methods",
    [
        ["resource1", {"PUT", "PATCH", "DELETE"}, {"GET", "POST", "OPTIONS"}],
        ["resource2", {"POST"}, {"GET", "PUT", "PATCH", "DELETE", "OPTIONS"}],
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


def test_optional_query_param_and_header_param(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_put(
        path=resource2.resource.api_route.format(country="ES", cityId=1),
        json_model=BasicInput(param1="test"),
    )
    assert resp.status_code == 200
    assert resp.json["data"]["tag"] is None
    assert resp.json["data"]["api_key"] is None


def test_optional_input_model(resource2: SimulatedResource) -> None:
    path = resource2.resource.api_route.format(country="ES", cityId=1)
    resp = resource2.simulate_put(path=path, json_model=BasicInput(param1="test"))
    assert resp.status_code == 200
    assert resp.json["data"]["param1"] == "test"

    resp_missing = resource2.simulate_put(path=path)
    assert resp_missing.status_code == 200
    assert resp_missing.json["data"]["param1"] is None


@pytest.mark.parametrize(
    "resource_fixture_name, exp_op_ids",
    [["resource1", {"getSomething", "postSomething"}], ["resource2", {"getCityData", "putCityData", "updateCityData"}]],
)
def test_openapi_generation(resource_fixture_name: str, exp_op_ids: set[str], request: pytest.FixtureRequest) -> None:
    sim_res: SimulatedResource = request.getfixturevalue(resource_fixture_name)
    result = sim_res.generate_openapi(
        title=sim_res.resource.__class__.__name__,
        version="0.0.1",
    )
    op_ids = set()
    for path_item in result.spec.paths.values():
        for name in vars(path_item):
            v = getattr(path_item, name)
            if isinstance(v, OpenApiOperation):
                op_ids.add(v.operation_id)
    assert op_ids == exp_op_ids
