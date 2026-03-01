import io
import types
from typing import Any, AsyncIterator, Literal

from falcon.typing import AsyncReadableIO, ReadableIO
from pydantic import BaseModel


def normalize_input(  # noqa: D103
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
    """Binary input or output for falcon-swoop operations.

    Note that this class can only be used for synchronous operations.
    """

    def __init__(
        self,
        binary: ReadableIO | bytes | str,
        content_length: int | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ):
        """Create binary for sync operations.

        :param binary: the actual binary, in case of ``str`` will be encoded according to ``charset``
        :param content_length: number of bytes in binary blob, recommended to provide this,
            for ``binary`` of type ``bytes`` or ``str`` this will be inferred
        :param content_type: MIME type of the binary
        :param charset: only relevant for text data, if a string is provided it will default to ``utf-8``
        """
        binary, content_type, charset = normalize_input(binary, content_type, charset)
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = io.BytesIO(binary)
        self.rio: ReadableIO = binary
        self.content_type = content_type
        self.content_length = content_length
        self.charset = charset

    def read(self, n: int | None = None) -> bytes:  # noqa: D102
        return self.rio.read(n)

    def text(
        self, errors: Literal["strict", "ignore", "replace", "backslashreplace", "surrogateescape"] = "strict"
    ) -> str:
        """Decode bytes into text."""
        raw = self.rio.read()
        return raw.decode(self.charset or "utf-8", errors=errors)


class AsyncBinaryIO:
    """Simple async wrapper for readable IO, required by falcon async resources."""

    def __init__(self, rio: ReadableIO, default_chunk_size: int = 8096):  # noqa: D107
        self.rio = rio
        self.default_chunk_size = default_chunk_size

    async def read(self, n: int | None = None) -> bytes:  # noqa: D102
        return self.rio.read(n)

    async def __aiter__(self) -> AsyncIterator[bytes]:  # noqa: D105
        while True:
            chunk = self.rio.read(self.default_chunk_size)
            yield chunk
            if len(chunk) < self.default_chunk_size:
                break


class OpAsgiBinary:
    """Binary input or output for falcon-swoop operations.

    Note that this class can only be used for asynchronous operations.
    """

    def __init__(
        self,
        binary: AsyncReadableIO | bytes | str,
        content_length: int | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ):
        """Create binary for async operations.

        :param binary: the actual binary, in case of ``str`` will be encoded according to ``charset``
        :param content_length: number of bytes in binary blob, recommended to provide this,
            for ``binary`` of type ``bytes`` or ``str`` this will be inferred
        :param content_type: MIME type of the binary
        :param charset: only relevant for text data, if a string is provided it will default to ``utf-8``
        """
        binary, content_type, charset = normalize_input(binary, content_type, charset)
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = AsyncBinaryIO(io.BytesIO(binary))
        self.rio: AsyncReadableIO = binary
        self.content_type = content_type
        self.content_length = content_length
        self.charset = charset

    async def read(self, n: int | None = None) -> bytes:  # noqa: D102
        return await self.rio.read(n)

    async def text(
        self, errors: Literal["strict", "ignore", "replace", "backslashreplace", "surrogateescape"] = "strict"
    ) -> str:
        """Decode bytes into text."""
        raw = await self.rio.read()
        return raw.decode(self.charset or "utf-8", errors=errors)


# TODO: add Multipart?
BODY_TYPES = (BaseModel, types.NoneType, OpBinary, OpAsgiBinary)
