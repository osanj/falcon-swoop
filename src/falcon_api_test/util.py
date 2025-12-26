from typing import Any

import falcon
from falcon.testing import TestClient, Result

from falcon_api import ApiBaseResource
from falcon_api.operation import HttpMethod


class SimulatedResource:

    def __init__(self, resource: ApiBaseResource) -> None:
        self.resource = resource
        app = falcon.App()
        app.add_route(resource.route.plain, resource)
        self.app = app
        self.client = falcon.testing.TestClient(self.app)

    def __get_path(self, kwargs: dict[str, Any]) -> str:
        default_path = self.resource.route.plain
        return str(kwargs.pop("path", default_path))

    def simulate_request(self, method: HttpMethod, **kwargs: Any) -> Result:
        return self.client.simulate_request(method, path=self.__get_path(kwargs), **kwargs)

    def simulate_get(self, **kwargs: Any) -> Result:
        return self.client.simulate_get(self.__get_path(kwargs), **kwargs)

    def simulate_post(self, **kwargs: Any) -> Result:
        return self.client.simulate_post(self.__get_path(kwargs), **kwargs)

    def simulate_put(self, **kwargs: Any) -> Result:
        return self.client.simulate_put(self.__get_path(kwargs), **kwargs)

    def simulate_patch(self, **kwargs: Any) -> Result:
        return self.client.simulate_patch(self.__get_path(kwargs), **kwargs)

    def simulate_delete(self, **kwargs: Any) -> Result:
        return self.client.simulate_delete(self.__get_path(kwargs), **kwargs)

    def simulate_head(self, **kwargs: Any) -> Result:
        return self.client.simulate_head(self.__get_path(kwargs), **kwargs)
