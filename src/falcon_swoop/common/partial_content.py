from pathlib import Path
from typing import Protocol

from falcon_swoop.binary import AsyncBinaryIO, OpAsgiBinary
from falcon_swoop.output import OpOutput


class ReadableAndSeekableIO(Protocol):
    def read(self, n: int | None = ..., /) -> bytes: ...
    def seek(self, pos: int, whence: int = 0) -> None: ...


DEFAULT_CHUNK_SIZE = 64 * 1024


def partial_file_asgi(
    path: Path,
    byte_range: tuple[int, int] | None = None,
    content_type: str = "application/octet-stream",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> OpOutput[OpAsgiBinary]:
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
    # https://www.rfc-editor.org/info/rfc9110/#status.206
    # https://www.rfc-editor.org/info/rfc9110/#name-byte-ranges

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
