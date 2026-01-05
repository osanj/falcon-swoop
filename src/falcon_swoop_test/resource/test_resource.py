import re

from falcon_swoop import operation, operation_doc
from falcon_swoop_test.resource.util import IMPL_ASYNC, IMPL_SYNC


def ensure_line_matches(line_sync: str, line_async: str, convert_def: bool = False) -> None:
    line_sync = line_sync.replace("self.ctx", "self.asgi_ctx")
    if convert_def:
        line_sync = line_sync.replace("def", "async def")
    assert line_sync == line_async


def test_ensure_sync_and_async_equivalence() -> None:
    with IMPL_ASYNC.open("r") as f:
        lines_async = f.readlines()

    with IMPL_SYNC.open("r") as f:
        lines_sync = f.readlines()

    assert len(lines_async) == len(lines_sync)

    pattern_operation_dec = f"\\s+@({operation.__name__}|{operation_doc.__name__})"
    pattern_falcon_method = f"def\\s+on_(post|get|put|delete|patch|head|options)"

    operation_expected = False
    for i in range(len(lines_sync)):
        line_async = lines_async[i]
        line_sync = lines_sync[i]

        has_falcon_method = re.search(pattern_falcon_method, line_sync) is not None
        ensure_line_matches(line_sync, line_async, operation_expected or has_falcon_method)
        operation_expected = re.match(pattern_operation_dec, line_sync) is not None
