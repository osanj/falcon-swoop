# falcon_api

Easy-to-define typed API operations with pydantic and automatic OpenAPI doc generation.
It is opt-in: Use the resource base class of this package whenever needed, other falcon resources will stay untouched.

### Open Items

- [ ] add binaryIO and textIO input/output data
- [ ] make certain query and header parameters optional (e.g. `my_query_param: int | None = ...`)
- [ ] warning that header params are case-insensitive (if name/alias provided that is not entirely upper/lowercase)
- [ ] warning for pydantic models that declare fields of type bytes
- [ ] add support for (de)serialization to yaml and other formats
- [ ] make everything work for async app
- [ ] grid CI pipeline testing combinations of python, falcon and pydantic
- [ ] include `py.typed` in package
- [ ] basic docs on README
