# falcon_api

Easy-to-define typed API operations with pydantic and automatic OpenAPI doc generation.
It is opt-in: Use the resource base class of this package whenever needed, other falcon resources will stay untouched.

### Open Items

- [ ] add params to openapi docgen
- [ ] add security schemes to openapi docgen
- [ ] add binaryIO and textIO input/output data
- [ ] make certain query and header parameters optional (e.g. `my_query_param: int | None = ...`)
- [ ] warning that header params are case-insensitive (if name/alias provided that is not entirely upper/lowercase)
- [ ] warning for pydantic models that declare fields of type bytes
- [ ] add support for optional input objects
- [ ] add support for (de)serialization to yaml and other formats
- [ ] add support for "more_response_docs" and way to annotate response with status + mime?
- [ ] make everything work for async app
- [ ] grid CI pipeline testing combinations of python, falcon and pydantic
- [ ] add unit test to make sure doc strings of operation and operation_doc are mostly identical
- [ ] remove `OpenApiMimeType`? (seems too restrictive)
- [ ] include `py.typed` in package
- [ ] basic docs on README
