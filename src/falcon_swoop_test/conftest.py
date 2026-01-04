from typing import Any

import pytest

from falcon_swoop_test.resource.util import SimulatedResourceLoader


@pytest.fixture(params=["asyncio"], scope="session")
def anyio_backend(request: pytest.FixtureRequest) -> Any:
    return request.param


@pytest.fixture(params=["sync", "async"], scope="session")
def resource_loader(request: pytest.FixtureRequest) -> SimulatedResourceLoader:
    return SimulatedResourceLoader(sync=request.param == "sync")
