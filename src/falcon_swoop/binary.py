from typing import Any, AsyncIterator, Literal
import io
import types

from pydantic import BaseModel
from falcon.typing import AsyncReadableIO, ReadableIO


def normalize_input(
    binary: Any | bytes | str,
    content_type: str | None,
    charset: str | None,
) -> tuple[Any | bytes, str | None, str | None]:
    if content_type is not None and "charset=" in content_type and charset is None:
        charset = content_type.split("charset=")[1].strip()
        content_type = content_type.split(";")[0]
    if isinstance(binary, str):
        if charset is None:
            charset = "utf-8"
        binary = binary.encode(encoding=charset)
    return binary, content_type, charset


class OpBinary:
    def __init__(
        self,
        binary: ReadableIO | bytes | str,
        content_length: int | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ):
        binary, content_type, charset = normalize_input(binary, content_type, charset)
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = io.BytesIO(binary)
        self.rio: ReadableIO = binary
        self.content_type = content_type
        self.content_length = content_length
        self.charset = charset

    def read(self, n: int | None = None) -> bytes:
        return self.rio.read(n)

    def text(
        self, errors: Literal["strict", "ignore", "replace", "backslashreplace", "surrogateescape"] = "strict"
    ) -> str:
        raw = self.rio.read()
        return raw.decode(self.charset or "utf-8", errors=errors)


class AsyncBinaryIO:
    def __init__(self, rio: ReadableIO):
        self.rio = rio

    async def read(self, n: int | None = None) -> bytes:
        return self.rio.read(n)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 8096
        while True:
            chunk = self.rio.read(size)
            yield chunk
            if len(chunk) < size:
                break


class OpAsgiBinary:
    def __init__(
        self,
        binary: AsyncReadableIO | bytes | str,
        content_length: int | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ):
        binary, content_type, charset = normalize_input(binary, content_type, charset)
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = AsyncBinaryIO(io.BytesIO(binary))
        self.rio: AsyncReadableIO = binary
        self.content_type = content_type
        self.content_length = content_length
        self.charset = charset

    async def read(self, n: int | None = None) -> bytes:
        return await self.rio.read(n)

    async def text(
        self, errors: Literal["strict", "ignore", "replace", "backslashreplace", "surrogateescape"] = "strict"
    ) -> str:
        raw = await self.rio.read()
        return raw.decode(self.charset or "utf-8", errors=errors)


# TODO: add Multipart?
BODY_TYPES = (BaseModel, types.NoneType, OpBinary, OpAsgiBinary)
