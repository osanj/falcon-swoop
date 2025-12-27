import pytest
from pydantic import BaseModel

from falcon_swoop import ApiBaseResource, operation, FalconApiConfigError, path_param, query_param


class DummyModel(BaseModel):
    pass


def test_config_error_for_duplicate_operations() -> None:
    class Resource(ApiBaseResource):
        @operation(method="GET")
        def get1(self) -> DummyModel:
            return DummyModel()

        @operation(method="GET")
        def get2(self) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match="Multiple functions are defined as GET"):
        Resource("/dummy")


def test_config_error_for_missing_operations() -> None:
    class Resource(ApiBaseResource):
        pass

    with pytest.raises(FalconApiConfigError, match="Found no operation"):
        Resource("/dummy")


def test_config_error_for_duplicate_path_params_in_route() -> None:
    class Resource(ApiBaseResource):
        pass

    with pytest.raises(FalconApiConfigError, match="Duplicate parameters were found in route"):
        Resource("/section/{param}/item/{param}")


def test_config_error_for_mismatching_path_parameters() -> None:
    exp_msg = "Found mismatch for path parameters defined for operation GET"

    class ResourceNoPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match=exp_msg):
        ResourceNoPathParam("/item/{item_id}")

    class ResourceWithPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match=exp_msg):
        ResourceWithPathParam("/item/")

    class ResourceWithBadPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self, id_of_item: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match=exp_msg):
        ResourceWithBadPathParam("/item/{item_id}")


def test_config_error_for_mismatching_path_parameter_with_alias() -> None:
    route = "/item/{itemId}"

    class Resource(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError):
        Resource(route)

    class ResourceWithAlias(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param(alias="itemId")) -> DummyModel:
            return DummyModel()

    ResourceWithAlias(route)


def test_config_error_for_complex_param_type() -> None:
    with pytest.raises(FalconApiConfigError, match="Query parameter query_params has unsupported type annotation"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self, query_params: dict[str, int] = query_param()) -> DummyModel:
                return DummyModel()
