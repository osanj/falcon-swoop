from datetime import datetime
from typing import Generic, Iterable, TypeVar

from pydantic import BaseModel

from falcon_swoop.binary import BODY_TYPES, OpAsgiBinary, OpBinary
from falcon_swoop.error import SwoopError

T = TypeVar("T", bound=BaseModel | OpBinary | OpAsgiBinary | None)


class OpOutput(Generic[T]):
    """Operation output wrapper for more control.

    Generally falcon-swoop operations return pydantic models or binary data directly. However, one may want to control
    other parts of the response, such as status code, content type and headers. For this OpOutput[<...>] can be used.
    """

    def __init__(
        self,
        payload: T,
        status_code: int | None = None,
        content_type: str | None = None,
        cache_control: str | Iterable[str] | None = None,
        etag: str | None = None,
        expires: str | datetime | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Create falcon-swoop operation output.

        :param payload: data that will go in the http body, can be pydantic model, binary or None
        :param status_code: optional status code, if ``None`` falcon-swoop will use the default status code
            configured in ``@operation(default_status=...)``
        :param content_type: optional content type, if ``None`` falcon-swoop will determine the content type
            based on the payload type or based on configuration if ``@operation(response_content_type=...)`` is used
        :param cache_control: optional cache-control header to control caching
        :param etag: optional etag header to control caching
        :param expires: optional expires header to control caching
        :param headers: any additional headers that shall be set on the response
        """
        self.payload = payload
        self.status_code = status_code
        self.content_type = content_type
        self.cache_control = cache_control
        self.etag = etag
        self.expires = expires
        self.headers: dict[str, str] = headers or {}

    @property
    def payload(self) -> T:
        """Data that will go in the HTTP body."""
        return self.__payload

    @payload.setter
    def payload(self, p: T) -> None:
        if not isinstance(p, BODY_TYPES):
            raise SwoopError(f"Operation output payload needs be one of {BODY_TYPES}, but got {type(p)}")
        self.__payload = p
