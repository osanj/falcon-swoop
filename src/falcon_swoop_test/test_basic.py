import pytest

from falcon_swoop.openapi.spec import OpenApiOperation
from falcon_swoop.operation import HttpMethod
from falcon_swoop_test.resource.common import WeatherLevel, BasicInput
from falcon_swoop_test.resource.util import SimulatedResource, SimulatedResourceLoader


@pytest.fixture(scope="module")
def resource1(resource_loader: SimulatedResourceLoader) -> SimulatedResource:
    return resource_loader.get("BasicResource1")


@pytest.fixture(scope="module")
def resource2(resource_loader: SimulatedResourceLoader) -> SimulatedResource:
    return resource_loader.get("BasicResource2")


@pytest.fixture(scope="module")
def resource3(resource_loader: SimulatedResourceLoader) -> SimulatedResource:
    return resource_loader.get("BasicResource3")


@pytest.fixture(scope="module")
def resource4(resource_loader: SimulatedResourceLoader) -> SimulatedResource:
    return resource_loader.get("BasicResource4")


def test_missing_input_raises_400(resource1: SimulatedResource) -> None:
    resp = resource1.simulate_post(json_model=BasicInput(param1="test"))
    assert resp.status_code == 200
    assert resp.json["data"]["param1"] == "test"

    resp_missing = resource1.simulate_post()
    assert resp_missing.status_code == 400


@pytest.mark.parametrize(
    "resource_name, methods, exp_allowed_methods",
    [
        ["BasicResource1", {"PUT", "PATCH", "DELETE"}, {"GET", "POST", "OPTIONS"}],
        ["BasicResource2", {"POST"}, {"GET", "PUT", "PATCH", "DELETE", "OPTIONS"}],
        ["BasicResource3", {"POST", "PATCH", "DELETE"}, {"GET", "PUT", "OPTIONS"}],
        ["BasicResource4", {"DELETE"}, {"GET", "POST", "PATCH", "PUT", "OPTIONS"}],
    ],
)
def test_unused_operation_raises_405(
    resource_name: str,
    methods: set[HttpMethod],
    exp_allowed_methods: set[HttpMethod],
    resource_loader: SimulatedResourceLoader,
) -> None:
    sim_res: SimulatedResource = resource_loader.get(resource_name)
    for method in methods:
        resp = sim_res.simulate_request(method=method)
        assert resp.status_code == 405, f"Unexpected status code for {method}"
        act_allowed_methods = set(am.strip() for am in resp.headers["allow"].split(","))
        assert act_allowed_methods == exp_allowed_methods, f"Unexpected allow header for {method}"


@pytest.mark.parametrize(
    "resource_name, exp_op_ids",
    [
        ["BasicResource1", {"getSomething", "postSomething"}],
        ["BasicResource2", {"getCityData", "putCityData", "updateCityData"}],
        ["BasicResource3", {"getWeather", "addWeatherSample"}],
        ["BasicResource4", {"getBlob", "getBlobStats", "addBlob", "addBlobStats"}],
    ],
)
def test_openapi_generation(resource_name: str, exp_op_ids: set[str], resource_loader: SimulatedResourceLoader) -> None:
    sim_res: SimulatedResource = resource_loader.get(resource_name)
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
    path = resource2.format_route(country="FR", cityId=1)
    expected_header_value = "not-dummy"

    resp0 = resource2.simulate_get(path=path)
    assert resp0.status_code == 200
    assert resp0.json["data"]["api_key"] != expected_header_value

    for header in ["X-API-KEY", "x-api-key", "X-ApI-kEy"]:
        resp0 = resource2.simulate_get(path=path, headers={header: expected_header_value})
        assert resp0.status_code == 200
        assert resp0.json["data"]["api_key"] == expected_header_value


def test_operation_decorated_with_docs_only(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_patch(path=resource2.format_route(country="ES", cityId=1))
    assert resp.status_code == 200
    assert resp.text == "patched"


def test_operation_not_decorated(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_delete(path=resource2.format_route(country="ES", cityId=1))
    assert resp.status_code == 200
    assert resp.text == "deleted"


def test_optional_query_param_and_header_param(resource2: SimulatedResource) -> None:
    resp = resource2.simulate_put(
        path=resource2.format_route(country="ES", cityId=1),
        json_model=BasicInput(param1="test"),
    )
    assert resp.status_code == 201
    assert resp.json["data"]["tag"] is None
    assert resp.json["data"]["api_key"] is None


def test_optional_input_model(resource2: SimulatedResource) -> None:
    path = resource2.format_route(country="ES", cityId=1)
    resp = resource2.simulate_put(path=path, json_model=BasicInput(param1="test"))
    assert resp.status_code == 201
    assert resp.json["data"]["param1"] == "test"

    resp_missing = resource2.simulate_put(path=path)
    assert resp_missing.status_code == 201
    assert resp_missing.json["data"]["param1"] is None


def test_string_enum(resource3: SimulatedResource) -> None:
    mode_input = WeatherLevel.REGIONAL.name
    resp_default = resource3.simulate_get()
    assert resp_default.status_code == 200
    assert resp_default.json["data"]["mode"] != mode_input  # ensure input is not default

    resp = resource3.simulate_get(params={"mode": mode_input})
    assert resp.status_code == 200
    assert resp.json["data"]["mode"] == mode_input

    resp_bad = resource3.simulate_get(params={"mode": "SPACE"})
    assert resp_bad.status_code == 400


def test_string_literal(resource3: SimulatedResource) -> None:
    unit_input = "F"
    resp_default = resource3.simulate_get()
    assert resp_default.status_code == 200
    assert resp_default.json["data"]["unit"] != unit_input  # ensure input is not default

    resp = resource3.simulate_get(params={"unit": unit_input})
    assert resp.status_code == 200
    assert resp.json["data"]["unit"] == unit_input

    resp_bad = resource3.simulate_get(params={"unit": "X"})
    assert resp_bad.status_code == 400


def test_status_code_via_output(resource3: SimulatedResource) -> None:
    input_model = BasicInput(param1="stormclouds are gathering")
    resp1 = resource3.simulate_put(params={"transient": False}, json_model=input_model)
    assert resp1.status_code == 201

    resp2 = resource3.simulate_put(params={"transient": True}, json_model=input_model)
    assert resp2.status_code == 200


def test_retrieve_http_binary(resource4: SimulatedResource) -> None:
    blob_id = 123
    path = resource4.format_route(blobId=blob_id)
    resp = resource4.simulate_get(path=path)
    exp_content = f"blob{blob_id}".encode("ascii")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    assert resp.content == exp_content
    assert int(resp.headers.get("content-length", 0)) == len(exp_content)


def test_retrieve_http_text(resource4: SimulatedResource) -> None:
    path = resource4.format_route(blobId=1)
    resp = resource4.simulate_patch(path=path)
    assert resp.status_code == 200
    assert resp.content_type == "text/csv"
    assert resp.encoding == "ISO-8859-1"
    lines = resp.text.split("\n")
    assert lines == ["stat;count", "sïzê;12345", "äccessés;123"]
