from enum import Enum, unique

import pytest
from pydantic import BaseModel

from falcon_swoop import (
    ApiBaseResource,
    FalconSwoopConfigError,
    FalconSwoopConfigWarning,
    OpAsgiContext,
    OpContext,
    OpAsgiBinary,
    OpBinary,
    operation,
    header_param,
    path_param,
    query_param,
    OpOutput,
    OpResponseDoc,
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
    with pytest.raises(
        FalconSwoopConfigError,
        match="Query parameter mode must be a string enum to be usable, "
              "either subclass from str and Enum or use StrEnum",
    ):

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
                mode: SummaryMode = query_param(),
            ) -> DummyModel:
                return DummyModel()


def test_config_error_for_bad_literal() -> None:
    with pytest.raises(
        FalconSwoopConfigError,
        match="Query parameter meta must only have literal values of type",
    ):
        from typing import Literal

        class Resource(ApiBaseResource):
            def __init__(self) -> None:
                super().__init__("/resource")

            @operation(method="GET")
            def get(
                self,
                meta: Literal[b"bad", "fine"] = query_param(),
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
        FalconSwoopConfigWarning,
        match="Header parameter accept has mixed case \\(see alias\\), but Header parameters are case insensitive",
    ):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(
                self,
                accept: str | None = header_param(alias="Accept", default=None),
            ) -> DummyModel:
                return DummyModel()


def test_config_error_for_multiple_contexts() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Duplicated context parameter"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self, ctx: OpContext, extra_ctx: OpContext) -> DummyModel:
                return DummyModel()


def test_config_error_for_wrong_context_type() -> None:
    with pytest.raises(
        FalconSwoopConfigError,
        match=f"Argument ctx has type {OpAsgiContext}, but expected {OpContext}",
    ):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self, ctx: OpAsgiContext) -> DummyModel:
                return DummyModel()


def test_config_error_for_output_without_type() -> None:
    with pytest.raises(
        FalconSwoopConfigError,
        match=f"The payload type for {OpOutput.__name__} is missing",
    ):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get(self) -> OpOutput:  # type: ignore[type-arg]
                return OpOutput(payload=None, status_code=400)


def test_config_output_with_none_is_possible() -> None:
    class Resource(ApiBaseResource):
        @operation(method="GET")
        def get(self) -> OpOutput[None]:
            return OpOutput(payload=None, status_code=400)


def test_config_error_for_default_status_code() -> None:
    status_code = 299
    with pytest.raises(
        FalconSwoopConfigError,
        match=f"Response docs for default HTTP status code {status_code} are generated",
    ):

        class Resource(ApiBaseResource):
            @operation(
                method="POST",
                default_status=(status_code, "Something was created"),
                more_response_docs={status_code: OpResponseDoc("Something else was done")},
            )
            def add_entry(self) -> None:
                pass


def test_config_error_for_async_binary_input_on_sync_operation() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is sync, but input type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="POST")
            def post_dummy(self, body: OpAsgiBinary) -> None:
                pass


def test_config_error_for_async_binary_output_on_sync_operation() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is sync, but return type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get_dummy(self) -> OpAsgiBinary:
                return OpAsgiBinary(b"test")


def test_config_error_for_async_binary_output_on_sync_operation_2() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is sync, but return type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            def get_dummy(self) -> OpOutput[OpAsgiBinary]:
                return OpOutput(OpAsgiBinary(b"test"), headers={"x-dummy": "dummy"})


def test_config_error_for_binary_input_on_async_operation() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is async, but input type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="POST")
            async def post_dummy(self, body: OpBinary) -> None:
                pass


def test_config_error_for_binary_output_on_async_operation() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is async, but return type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            async def get_dummy(self) -> OpBinary:
                return OpBinary(b"test")


def test_config_error_for_binary_output_on_async_operation_2() -> None:
    with pytest.raises(FalconSwoopConfigError, match="Operation is async, but return type is configured as"):

        class Resource(ApiBaseResource):
            @operation(method="GET")
            async def get_dummy(self) -> OpOutput[OpBinary]:
                return OpOutput(OpBinary(b"test"), headers={"x-dummy": "dummy"})
