import pytest
from pydantic import BaseModel

from falcon_api import ApiBaseResource, operation, FalconApiConfigError, ApiPathParam


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
        def get(self, item_id: str = ApiPathParam()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match=exp_msg):
        ResourceWithPathParam("/item/")

    class ResourceWithBadPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self, id_of_item: str = ApiPathParam()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError, match=exp_msg):
        ResourceWithBadPathParam("/item/{item_id}")


def test_config_error_for_mismatching_path_parameter_with_alias() -> None:
    route = "/item/{itemId}"

    class Resource(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = ApiPathParam()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconApiConfigError):
        Resource(route)

    class ResourceWithAlias(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = ApiPathParam(alias="itemId")) -> DummyModel:
            return DummyModel()

    ResourceWithAlias(route)
