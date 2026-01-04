import re
from pathlib import Path

from falcon_swoop import operation, operation_doc


def test_ensure_sync_and_async_equivalence() -> None:
    file_dir = Path(__file__).parent
    file_async = file_dir / "impl_async.py"
    file_sync = file_dir / "impl_sync.py"

    with file_async.open("r") as f:
        lines_async = f.readlines()

    with file_sync.open("r") as f:
        lines_sync = f.readlines()

    assert len(lines_async) == len(lines_sync)

    pattern_operation_dec = f"\\s+@({operation.__name__}|{operation_doc.__name__})"
    pattern_falcon_method = f"def\\s+on_(post|get|put|delete|patch|head|options)"

    def ensure_line_matches(line_sync_: str, line_async_: str, convert_def: bool = False) -> None:
        if convert_def:
            line_sync_ = line_sync.replace("def", "async def")
        assert line_sync_ == line_async_

    operation_expected = False
    for i in range(len(lines_sync)):
        line_async = lines_async[i]
        line_sync = lines_sync[i]

        has_falcon_method = re.search(pattern_falcon_method, line_sync) is not None
        ensure_line_matches(line_sync, line_async, operation_expected or has_falcon_method)
        operation_expected = re.match(pattern_operation_dec, line_sync) is not None
