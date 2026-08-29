import io
from typing import BinaryIO, Callable

from falcon_swoop import (
    OpAsgiBinary,
    OpAsgiContext,
    OpOutput,
    SwoopResource,
    operation,
)
from falcon_swoop.common.partial_content import DEFAULT_CHUNK_SIZE, ReadableAndSeekableIO, partial_content_asgi
from falcon_swoop_test.resource.util import SimulatedResource


class PartialContentDemo(SwoopResource):
    def __init__(self, open_io: Callable[[], tuple[BinaryIO, int]], chunk_size: int = DEFAULT_CHUNK_SIZE):
        super().__init__("/big-file")
        self.open_io = open_io
        self.chunk_size = chunk_size

    @operation(method="GET")
    async def get_big_file(self, ctx: OpAsgiContext) -> OpOutput[OpAsgiBinary]:
        bio: ReadableAndSeekableIO
        bio, size = self.open_io()  # type: ignore[assignment]
        return partial_content_asgi(
            bio=bio,
            bio_size=size,
            byte_range=ctx.req.range,
            chunk_size=self.chunk_size,
        )


def test_partial_content_responses() -> None:
    original_bytes = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = len(original_bytes)
    chunk_size = n // 4

    def get_bio() -> tuple[BinaryIO, int]:
        return io.BytesIO(original_bytes), n

    demo = PartialContentDemo(get_bio, chunk_size=chunk_size)
    resource = SimulatedResource(demo, sync=False)

    resp1 = resource.simulate_get()
    assert resp1.status_code == 200
    assert resp1.headers.get("Accept-Ranges") == "bytes"
    assert len(resp1.content) == n

    a = chunk_size
    b = n - a - 1
    resp2 = resource.simulate_get(headers={"Range": f"bytes={a}-{b}"})
    assert resp2.status_code == 206
    assert resp2.content == original_bytes[a : b + 1]
    assert resp2.headers.get("Content-Range") == f"bytes {a}-{b}/{n}"

    resp3 = resource.simulate_get(headers={"Range": "bytes=0-1"})
    assert resp3.status_code == 206
    assert resp3.content == original_bytes[:2]
    assert resp3.headers.get("Content-Range") == f"bytes 0-1/{n}"
