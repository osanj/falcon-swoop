import importlib
from pathlib import Path
from typing import Any

import falcon
import falcon.asgi
from falcon.testing import Result
from pydantic import BaseModel

from falcon_swoop import OpenApiGenerator, OpenApiGeneratorResult, OpenApiGeneratorSettings, SwoopResource
from falcon_swoop.operation_spec import HttpMethod


class SimulatedResource:
    def __init__(self, resource: SwoopResource, sync: bool = True) -> None:
        self.resource = resource
        app = falcon.App() if sync else falcon.asgi.App()
        app.add_route(resource.api_route.plain, resource)
        self.app = app
        self.client = falcon.testing.TestClient(self.app)

    @property
    def plain_route(self) -> str:
        return self.resource.api_route.plain

    def format_route(self, **kwargs: Any) -> str:
        return self.resource.api_route.format(**kwargs)

    def __get_path(self, kwargs: dict[str, Any]) -> str:
        return str(kwargs.pop("path", self.plain_route))

    def __convert_model_to_json(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        key_json = "json"
        key_model = "json_model"
        if key_json in kwargs and key_model in kwargs:
            raise RuntimeError(f"The keyword argument {key_model} cannot be used if {key_json} is also used")
        model_input = kwargs.pop(key_model, None)
        if model_input is not None:
            assert isinstance(model_input, BaseModel), f"{key_model} argument must be {BaseModel.__name__}"
            kwargs[key_json] = model_input.model_dump(by_alias=True)
        return kwargs

    def simulate_request(self, method: HttpMethod, **kwargs: Any) -> Result:
        return self.client.simulate_request(
            method,
            path=self.__get_path(kwargs),
            **self.__convert_model_to_json(kwargs),
        )

    def simulate_get(self, **kwargs: Any) -> Result:
        return self.client.simulate_get(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def simulate_post(self, **kwargs: Any) -> Result:
        return self.client.simulate_post(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def simulate_put(self, **kwargs: Any) -> Result:
        return self.client.simulate_put(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def simulate_patch(self, **kwargs: Any) -> Result:
        return self.client.simulate_patch(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def simulate_delete(self, **kwargs: Any) -> Result:
        return self.client.simulate_delete(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def simulate_head(self, **kwargs: Any) -> Result:
        return self.client.simulate_head(self.__get_path(kwargs), **self.__convert_model_to_json(kwargs))

    def generate_openapi(
        self,
        title: str,
        version: str,
        summary: str | None = None,
        description: str | None = None,
        settings: OpenApiGeneratorSettings | None = None,
    ) -> OpenApiGeneratorResult:
        generator = OpenApiGenerator(
            resources=[self.resource],
            title=title,
            version=version,
            summary=summary,
            description=description,
            settings=settings,
        )
        return generator.generate()


IMPL_ASYNC = Path(__file__).parent / "impl_async.py"
IMPL_SYNC = Path(__file__).parent / "impl_sync.py"


class SimulatedResourceLoader:
    def __init__(self, sync: bool = True) -> None:
        self.sync = sync

    def get(self, resource_name: str) -> SimulatedResource:
        impl = IMPL_SYNC if self.sync else IMPL_ASYNC
        module_path = f".{impl.stem}"

        try:
            module = importlib.import_module(module_path, package=__package__)
            resource_class = getattr(module, resource_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not load {resource_name} from {module_path}: {e}")

        resource_obj = resource_class()
        return SimulatedResource(resource_obj, sync=self.sync)
