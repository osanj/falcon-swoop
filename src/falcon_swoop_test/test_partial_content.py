import io
from typing import BinaryIO, Callable

from falcon_swoop import (
    OpAsgiBinary,
    OpAsgiContext,
    OpOutput,
    operation,
    SwoopResource,
)
from falcon_swoop.common.partial_content import partial_content_asgi, DEFAULT_CHUNK_SIZE
from falcon_swoop_test.resource.util import SimulatedResource


class PartialContentDemo(SwoopResource):

    def __init__(self, open_io: Callable[[], tuple[BinaryIO, int]], chunk_size: int = DEFAULT_CHUNK_SIZE):
        super().__init__("/big-file")
        self.open_io = open_io
        self.chunk_size = chunk_size

    @operation(method="GET")
    async def get_big_file(self, ctx: OpAsgiContext) -> OpOutput[OpAsgiBinary]:
        bio, size = self.open_io()
        return partial_content_asgi(
            bio=bio,
            bio_size=size,
            byte_range=ctx.req.range,
            chunk_size=self.chunk_size,
        )


def test_partial_content_responses() -> None:
    original_bytes = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    cunk_size = len(original_bytes) // 10

    def get_bio() -> tuple[BinaryIO, int]:
        return io.BytesIO(original_bytes), len(original_bytes)

    demo = PartialContentDemo(get_bio, chunk_size=cunk_size)
    resource = SimulatedResource(demo, sync=False)

    resp1 = resource.simulate_get()
    assert resp1.status_code == 200
    assert resp1.headers.get("Accept-Ranges") == "bytes"
    content_size = len(resp1.content)
    assert content_size == chunk_size
    assert content_size < resp1["Content-Length"]
