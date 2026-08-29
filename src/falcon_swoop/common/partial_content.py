from pathlib import Path
from typing import Protocol

from falcon_swoop.binary import AsyncBinaryIO, OpAsgiBinary
from falcon_swoop.output import OpOutput


class ReadableAndSeekableIO(Protocol):
    """File-like protocol that defines a read as well as a seek method."""

    def read(self, n: int | None = ..., /) -> bytes: ...  # noqa: D102
    def seek(self, pos: int, whence: int = 0, /) -> int: ...  # noqa: D102


DEFAULT_CHUNK_SIZE = 64 * 1024


def partial_file_asgi(
    path: Path,
    byte_range: tuple[int, int] | None = None,
    content_type: str = "application/octet-stream",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> OpOutput[OpAsgiBinary]:
    """File utility function to build binary output for requests with ``Range`` header (206 partial content).

    For more details see doc string of ``partial_content_asgi``.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Provided path does not point to a file: {path}")
    bio = path.open(mode="rb")
    size = path.stat().st_size
    return partial_content_asgi(bio, size, byte_range, content_type, chunk_size)


def partial_content_asgi(
    bio: ReadableAndSeekableIO,
    bio_size: int,
    byte_range: tuple[int, int] | None = None,
    content_type: str = "application/octet-stream",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> OpOutput[OpAsgiBinary]:
    """Byte stream utility function to build binary output for requests with ``Range`` header (206 partial content).

    Implements `206 Partial Content` partially (no pun intended). Only supports "single part" requests, multiple ranges
    in the request are not supported, e.g. `Range: bytes=234-639,4590-7999` (which apparently is uncommon anyway).
    This is function is still useful for instance browsers do partial requests for ``<video>`` tags, this enables
    a quick start of the stream even if the entire video has not been retrieved yet.

    See https://www.rfc-editor.org/info/rfc9110/#status.206 and https://www.rfc-editor.org/info/rfc9110/#name-byte-ranges.

    :param bio: binary IO, must be readable and seekable
    :param bio_size: size of the binary IO
    :param byte_range: parsed ``Range`` header, falcon provides this in its request objects, for instance: ``req.range``
        (add an falcon swoop context object to your operation inputs to access the raw request: ``ctx.req.range``)
    :param content_type: content type of the binary IO
    :param chunk_size: size in bytes of the chunks that are streamed into the response back to the client
    """
    # normal response in case no range is provided
    if byte_range is None:
        wrapper = AsyncBinaryIO(bio, iter_chunk_size=chunk_size)
        return OpOutput(
            payload=OpAsgiBinary(wrapper, content_length=bio_size, content_type=content_type),
            headers={"Accept-Ranges": "bytes"},
            status_code=200,
        )

    a, b = byte_range
    if a < 0:
        a = bio_size + a
    if b < 0:
        b = bio_size + b
    range_size = b - a + 1
    bio.seek(a)
    wrapper = AsyncBinaryIO(bio, iter_chunk_size=chunk_size, max_read_size=range_size)
    return OpOutput(
        payload=OpAsgiBinary(wrapper, content_length=range_size, content_type=content_type),
        headers={"Accept-Ranges": "bytes", "Content-Range": f"bytes {a}-{b}/{byte_range}"},
        status_code=206,
    )
