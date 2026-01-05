# falcon-swoop

Easy-to-define typed API resources for [falcon](https://github.com/falconry/falcon) based on [pydantic](https://github.com/pydantic/pydantic) models.
Automatic OpenAPI doc generation included. Fully opt-in: Use it for all your resources, start attaching typed operations
to an existing app or just add a single typed resource to your project.


### Open Items

- [ ] add params to openapi docgen
- [ ] add security schemes to openapi docgen
- [ ] add binaryIO and textIO input/output data
- [x] make certain query and header parameters optional (e.g. `my_query_param: int | None = ...`)
- [x] allow literal and str-Enum for parameters
- [x] warning that header params are case-insensitive (if name/alias provided that is not entirely upper/lowercase)
- [ ] warning for pydantic models that declare fields of type bytes
- [x] add support for optional input objects
- [ ] add support for (de)serialization to yaml and other formats
- [ ] add support for "more_response_docs" and way to annotate response with status + mime?
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
