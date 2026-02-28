from datetime import datetime
from typing import Generic, Iterable, TypeVar

from pydantic import BaseModel

from falcon_swoop.error import FalconSwoopError
from falcon_swoop.binary import BODY_TYPES


T = TypeVar("T", bound=BaseModel | None)


class OpOutput(Generic[T]):

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
        self.payload = payload
        self.status_code = status_code
        self.content_type = content_type
        self.cache_control = cache_control
        self.etag = etag
        self.expires = expires
        self.headers: dict[str, str] = headers or {}

    @property
    def payload(self) -> T:
        return self.__payload

    @payload.setter
    def payload(self, p: T) -> None:
        if not isinstance(p, BODY_TYPES):
            raise FalconSwoopError(f"Operation output payload needs be one of {BODY_TYPES}, but got {type(p)}")
        self.__payload = p
