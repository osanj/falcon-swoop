import falcon
import falcon.asgi

from falcon_swoop.openapi.gen import OpenApiGenerator, OpenApiGeneratorHook, OpenApiGeneratorSettings
from falcon_swoop.openapi.resource import (
    OpenApiAsgiResource,
    OpenApiResource,
    OpenApiSwaggerAsgiResource,
    OpenApiSwaggerResource,
)
from falcon_swoop.openapi.swagger import OpenApiSwaggerUiSettings
from falcon_swoop.resource import SwoopResource


class SwoopApp:
    """Wrapper class for setting up falcon-swoop resources."""

    def __init__(
        self,
        app: falcon.App | falcon.asgi.App,  # type: ignore
        title: str,
        version: str,
        summary: str | None = None,
        description: str | None = None,
        spec_json_route: str | None = "/api.json",
        spec_swagger_route: str | None = "/api.html",
        generator_settings: OpenApiGeneratorSettings | None = None,
        generator_hook: OpenApiGeneratorHook | None = None,
        swagger_ui_settings: OpenApiSwaggerUiSettings | None = None,
    ):
        """Initialize a falcon-swoop OpenAPI application.

        Use this class to wrap your falcon app object and register falcon-swoop API resources. By default,
        resources for serving the spec as JSON and Swagger HTML are added automatically. The original falcon ``app``
        object can be used before and afterward as usual, however only resources added via this class end up
        in the OpenAPI spec. Here is an example::

            import falcon
            from falcon-swoop import SwoopApp

            app = falcon.App()
            app.add_route("/some/route", SomeResource())  # not in the spec

            openapi = SwoopApp(app, title="SomeApp", version="1.0.0")
            openapi.add_route(SomeSwoopResource())  # in the spec
            openapi.add_route(SomeOtherSwoopResource())  # in the spec

            app.add_sink(StaticSink(), "/static")  # not in the spec


        :param title: title in the OpenAPI spec
        :param version: version in the OpenAPI spec
        :param summary: summary in the OpenAPI spec
        :param description: description in the OpenAPI spec
        :param spec_json_route: route where the OpenAPI spec shall be served, use ``None`` to deactivate
        :param spec_swagger_route: route where the OpenAPI swagger shall be served, use ``None`` to deactivate
        :param generator_settings: optional settings for the generation of the OpenAPI specification
        :param generator_hook: optional hook to edit the OpenAPI generated specification before it is used by
            the endpoint serving the spec as JSON, useful to add things that falcon-swoop doesn't generate
        :param swagger_ui_settings: optional settings for the swagger UI rendering of the OpenAPI specification
        """
        self.app = app
        self.generator = OpenApiGenerator(
            title=title,
            version=version,
            summary=summary,
            description=description,
            settings=generator_settings,
            after_generation=generator_hook,
        )
        is_sync = not isinstance(app, falcon.asgi.App)
        if spec_json_route is not None:
            if is_sync:
                self.add_route(OpenApiResource(self.generator, spec_json_route))
            else:
                self.add_route(OpenApiAsgiResource(self.generator, spec_json_route))
        if spec_swagger_route is not None:
            if spec_json_route is None:
                raise ValueError("The swagger endpoint needs a JSON spec route, please provide a JSON route")
            if is_sync:
                self.add_route(
                    OpenApiSwaggerResource(
                        spec_swagger_route,
                        spec_json_route,
                        title=title,
                        settings=swagger_ui_settings,
                    )
                )
            else:
                self.add_route(
                    OpenApiSwaggerAsgiResource(
                        spec_swagger_route,
                        spec_json_route,
                        title=title,
                        settings=swagger_ui_settings,
                    )
                )

    def add_route(self, resource: SwoopResource) -> None:
        """Add API resource."""
        if not isinstance(resource, SwoopResource):
            raise ValueError(f"Only resources of type {SwoopResource.__name__} can be registered")
        self.app.add_route(resource.api_route.plain, resource)
        self.generator.add_resource(resource)
