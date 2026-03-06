import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenApiSwaggerUiSettings:  # noqa: D101
    css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"

    # https://github.com/swagger-api/swagger-ui/blob/HEAD/docs/usage/configuration.md
    doc_expansion: str = "list"
    operations_sorter: str = "alpha"
    default_models_expand_depth: int = 2
    default_model_expand_depth: int = 2
    other: dict[str, Any] = field(default_factory=dict)


def build_swagger_ui_html(
    openapi_url_relative: str,
    title: str,
    settings: OpenApiSwaggerUiSettings | None = None,
) -> str:
    """Generate a HTML document that renders an OpenAPI spec endpoint in swagger.

    :param openapi_url_relative: relative url to openapi document
    :param title: HTML page title
    :param settings: more settings, see also https://github.com/swagger-api/swagger-ui/blob/HEAD/docs/usage/configuration.md
    """
    # based on https://github.com/fastapi/fastapi/blob/0.133.0/fastapi/openapi/docs.py

    settings = settings or OpenApiSwaggerUiSettings()
    config = dict(settings.other)
    config.update(
        {
            "url": openapi_url_relative,
            "dom_id": "#swagger-ui",
            "deepLinking": True,
            "layout": "BaseLayout",
            "docExpansion": settings.doc_expansion,
            "operationsSorter": settings.operations_sorter,
            "defaultModelsExpandDepth": settings.default_models_expand_depth,
            "defaultModelExpandDepth": settings.default_model_expand_depth,
        }
    )

    data = json.dumps(config)
    data_html_safe = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <link type="text/css" rel="stylesheet" href="{settings.css_url}">
        <title>{title}</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="{settings.js_url}"></script>
        <script>
        window.onload = function() {{
            // Swagger UI config
            const config = {data_html_safe};
            config.presets = [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ];
            const ui = SwaggerUIBundle(config);
            window.ui = ui;
        }};
        </script>
    </body>
    </html>
    """
