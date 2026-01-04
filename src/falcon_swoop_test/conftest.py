import pytest

from falcon_swoop_test.resource.util import SimulatedResourceLoader


@pytest.fixture(params=["sync", "async"], scope="session")
def resource_loader(request: pytest.FixtureRequest) -> SimulatedResourceLoader:
    return SimulatedResourceLoader(sync=request.param == "sync")
