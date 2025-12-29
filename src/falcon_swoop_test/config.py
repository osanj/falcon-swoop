from enum import Enum, unique

import pytest
from pydantic import BaseModel

from falcon_swoop import (
    ApiBaseResource,
    FalconSwoopConfigError,
    FalconSwoopConfigWarning,
    operation,
    header_param,
    path_param,
    query_param,
)


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

    with pytest.raises(FalconSwoopConfigError, match="Multiple functions are defined as GET"):
        Resource("/dummy")


def test_config_error_for_missing_operations() -> None:
    class Resource(ApiBaseResource):
        pass

    with pytest.raises(FalconSwoopConfigError, match="Found no operation"):
        Resource("/dummy")


def test_config_error_for_duplicate_path_params_in_route() -> None:
    class Resource(ApiBaseResource):
        pass

    with pytest.raises(FalconSwoopConfigError, match="Duplicate parameters were found in route"):
        Resource("/section/{param}/item/{param}")


def test_config_error_for_mismatching_path_parameters() -> None:
    exp_msg = "Found mismatch for path parameters defined for operation GET"

    class ResourceNoPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconSwoopConfigError, match=exp_msg):
        ResourceNoPathParam("/item/{item_id}")

    class ResourceWithPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconSwoopConfigError, match=exp_msg):
        ResourceWithPathParam("/item/")

    class ResourceWithBadPathParam(ApiBaseResource):
        @operation(method="GET")
        def get(self, id_of_item: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconSwoopConfigError, match=exp_msg):
        ResourceWithBadPathParam("/item/{item_id}")


def test_config_error_for_mismatching_path_parameter_with_alias() -> None:
    route = "/item/{itemId}"

    class Resource(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param()) -> DummyModel:
            return DummyModel()

    with pytest.raises(FalconSwoopConfigError):
        Resource(route)

    class ResourceWithAlias(ApiBaseResource):
        @operation(method="GET")
        def get(self, item_id: str = path_param(alias="itemId")) -> DummyModel:
            return DummyModel()

    ResourceWithAlias(route)


def test_config_error_for_complex_param_type() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Query parameter query_params has unsupported type annotation"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self, query_params: dict[str, int] = query_param()) -> DummyModel:
                return DummyModel()


def test_config_error_for_missing_param_type() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Query parameter param requires type annotation"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self, param=query_param()) -> DummyModel:  # type: ignore[no-untyped-def]
                return DummyModel()


def test_config_error_for_optional_return_value() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Return type cannot be a union or optional"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self) -> DummyModel | None:
                return DummyModel()


def test_config_error_for_optional_path_parameter() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Path parameter resource_id cannot be optional"):

        class Resource(ApiBaseResource):
            def __init__(self) -> None:
                super().__init__("/resource/{resourceId}")

            @operation(method="GET")
            def get(
                self,
                resource_id: int | None = path_param(alias="resourceId"),
                min_size: int | None = query_param(alias="minSize"),
            ) -> DummyModel:
                return DummyModel()


def test_config_error_for_normal_enum() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Query parameter mode cannot be an enum, only string enums (class MyEnum(str, Enum)) are possible"):

        @unique
        class SummaryMode(Enum):
            SHORT = "SHORT"
            FULL = "FULL"

        class Resource(ApiBaseResource):
            def __init__(self) -> None:
                super().__init__("/summary")

            @operation(method="GET")
            def get(
                self,
                mode: SummaryMode = header_param(),
            ) -> DummyModel:
                return DummyModel()


def test_config_warning_for_optional_parameter_with_default() -> None:
    with pytest.warns(
        FalconSwoopConfigWarning, match="Query parameter max_size is type hinted as optional, but will never be None"
    ):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(
                self,
                min_size: int | None = query_param(alias="minSize", default=None),
                max_size: int | None = query_param(alias="maxSize", default=10),
            ) -> DummyModel:
                return DummyModel()


def test_config_warning_for_header_case_insensitivity() -> None:
    with pytest.warns(
        FalconSwoopConfigWarning, match="Header parameter accept (or its alias) has mixed case, but HTTP headers are case insensitive, it can be defined completely lowercase or uppercase"
    ):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(
                self,
                accept: str | None = header_param(alias="Accept", default=None),
            ) -> DummyModel:
                return DummyModel()
