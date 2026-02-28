from typing import AsyncIterator, BinaryIO, Literal
import io
import types

from pydantic import BaseModel
from falcon.typing import AsyncReadableIO, ReadableIO


class AsyncBinaryIO:

    def __init__(self, rio: ReadableIO):
        self.rio = rio

    async def read(self, n: int | None = ..., /) -> bytes:
        return self.rio.read(n)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 8096
        while True:
            chunk = self.rio.read(size)
            yield chunk
            if len(chunk) < size:
                break


class HttpBinary:

    def __init__(
        self,
        binary: BinaryIO | bytes,
        content_length: int | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ):
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = io.BytesIO(binary)
        self.bio = binary
        self.content_type = content_type
        self.content_length = content_length
        self.charset = charset

    def as_async_buffer(self) -> AsyncReadableIO:
        return AsyncBinaryIO(self.bio)


class HttpText(HttpBinary):

    def __init__(self, text: str, content_type: str | None = None, charset: str = "utf-8"):
        text_bytes = text.encode(encoding=charset)
        super().__init__(
            binary=text_bytes,
            content_type=content_type,
        )

    def text(
        self, errors: Literal["strict", "ignore", "replace", "backslashreplace", "surrogateescape"] = "strict"
    ) -> str:
        raw = self.bio.read()
        return raw.decode(self.charset or "utf-8", errors=errors)


# TODO: add Multipart?
BODY_TYPES = (BaseModel, types.NoneType, HttpBinary, HttpText)
