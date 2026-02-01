# falcon-swoop

Easy-to-define typed API resources for [falcon](https://github.com/falconry/falcon) based on [pydantic](https://github.com/pydantic/pydantic) models bringing some FastAPI style
convenience to your favorite web framework. Automatic OpenAPI doc generation included.
It is fully opt-in: Use it for all your resources, start attaching typed operations
to an existing app or just add one single typed resource to your project.


### Open Items

- [x] add params to openapi docgen
- [ ] add security schemes to openapi docgen
- [ ] add binaryIO and textIO input/output data
  - [x] keep api resource stateless -> if context is needed it should be declared as input to the method
  - [ ] set up classes for binaryIO (and textIO?)
  - [x] implement usage of default status for operation and add test
  - [x] add generic class holding output, where more details can be set
  - [x] make generic class holding output compatible with None
  - [ ] check "more_response_docs" compatibility, what if default status is defined there again?
  - [ ] sketch out Multipart form data?
- [x] make certain query and header parameters optional (e.g. `my_query_param: int | None = ...`)
- [x] allow literal and str-Enum for parameters
- [x] warning that header params are case-insensitive (if name/alias provided that is not entirely upper/lowercase)
- [ ] warning for pydantic models that declare fields of type bytes
- [x] add support for optional input objects
- [ ] add support for (de)serialization to yaml and other formats
- [ ] add support for "more_response_docs" and way to annotate response with status + mime?
- [ ] handle missing annotations for input, params, context and return value
- [ ] use `falcon._typing.ResponderCallable` and async types or redefine proper callable types
- [x] make everything work for async app
- [ ] grid CI pipeline testing combinations of python, falcon and pydantic
- [ ] add unit test to make sure doc strings of operation and operation_doc are mostly identical
- [ ] make sure snake_case to camelCase works easily (especially for query and path params)
- [ ] remove `OpenApiMimeType`? (seems too restrictive)
- [x] include `py.typed` in package
- [ ] rich docstrings on operation, operation_doc and possibly other frequently used symbols
- [ ] basic docs on README

### User Guide

quick start, walkthrough (operation, operation_doc, generator)

### Development Guide

```
pip install .  # to install main dependencies
pip install -e ".[dev]"  # to install main and dev dependencies

black
mypy
pytest -v

hatchling build -t wheel
```
