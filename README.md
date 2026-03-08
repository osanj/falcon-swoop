# falcon-swoop

Easy-to-define typed API resources for [falcon](https://github.com/falconry/falcon) based on [pydantic](https://github.com/pydantic/pydantic) models bringing some FastAPI style
convenience to your favorite web framework. Automatic OpenAPI doc generation included.
It is fully opt-in: Use it for all your resources, start attaching typed operations
to an existing app or just add a single typed resource to your project.
OpenAPI documentation can also be added manually for old or very complex operations that don't fit in this framework.

Compatible with Falcon 4.x and Pydantic 2.x.


## User Guide

### Quickstart

To use falcon-swoop follow these steps:
1. subclass from `SwoopResource`
2. create a method for your API operation and type-hint it with Pydantic classes for input and output
3. decorate that method with `@operation`
4. wrap the falcon `App` with `SwoopApp` and register the swoop resources there


```python
import falcon.asgi
from falcon_swoop import SwoopApp, SwoopResource, operation
from pydantic import BaseModel, Field


def store_message_in_db(author: str, text: str) -> str:
  # implement storage in database here!
  return "new_id"


class CreateMessageInput(BaseModel):
  author: str
  text: str = Field(min_length=20)

  
class CreateMessageOutput(BaseModel):
  message_uid: str

  
class NewMessageController(SwoopResource):
  def __init__(self):
    super().__init__(route="/api/message")
      
  @operation(method="POST")
  async def create_message(self, message: CreateMessageInput) -> CreateMessageOutput:
    message_uid = store_message_in_db(message.author, message.text)
    return CreateMessageOutput(message_uid=message_uid)

  
def build_app() -> falcon.asgi.App:
  app = falcon.asgi.App()
  swoop = SwoopApp(
    app,
    title="Example App",
    version="0.1.0",
    spec_json_route="/api/openapi.json",
    spec_swagger_route="/api/swagger.html",
  )
  swoop.add_route(NewMessageController)
  return app
```

Once the application is running, new JSON data can be submitted on `POST /message` according to `CreateMessageInput`,
similarly the application will respond with JSON according to `CreateMessageOutput`. The OpenAPI specification can then
be accessed as JSON on `/api/openapi.json` or human-readable at `/api/swagger.html`.

This concludes the basics, keep reading for more details!


### Tips

* falcon-swoop works for both synchronous and asynchronous falcon applications
* for operations that are too complicated for falcon-swoop, but should still show up in the OpenAPI specification, the `@operation_doc` decorator can be used to provide manual documentation on conventional falcon responder methods, such as `on_get`, `on_post` and so on
* use `header_param`, `query_param` and `path_param` to model inputs other than the HTTP body
* for binary input and output use `OpBinary` (or `OpAsgiBinary` for async operations)
* for more finegrained response control (status code, headers, ...) return `OpOutput[SomeModel]` or  `OpOutput[OpBinary]`
* when access to the entire falcon request and response is required, add an input with `OpContext` (or `OpAsgiContext` for async operations)


### Full Example

Check out [src/falcon_swoop_example](src/falcon_swoop_example) for a full example. To run it `gunicorn` needs to be
installed, then the application can be started with the commands below. Check the logs on which routes the OpenAPI
specification and the Swagger UI can be accessed.
```
cd src
./falcon_swoop_example.sh
```


## Development Guide

```
pip install .  # to install main dependencies
pip install -e ".[dev]"  # to install main and dev dependencies

ruff check --fix
ruff format
mypy
pytest -v
nox  # requires separate install

hatchling build -t wheel
```


## Open Items

- [ ] add security schemes to openapi docgen
- [ ] warning for pydantic models that declare fields of type bytes
- [ ] handle missing annotations for input, params, context and return value
- [ ] add support for (de)serialization to yaml and other formats
- [ ] utility spec class for Multipart form data
  - [ ] makes parsing easy
  - [ ] integrates with OpenAPI generation
- [ ] make sure snake_case to camelCase works easily (especially for query and path params)
