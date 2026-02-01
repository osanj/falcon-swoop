from typing import BinaryIO, TextIO
import io


class HttpBinary:

    def __init__(self, binary: BinaryIO | bytes, content_type: str | None = None, content_length: int | None = None):
        if isinstance(binary, bytes):
            content_length = len(binary)
            binary = io.BytesIO(binary)
        self.bio = binary
        self.content_type = content_type
        self.content_length = content_length


class HttpText:

    def __init__(self, text: TextIO | str, content_type: str | None = None, content_length: int | None = None):
        if isinstance(text, str):
            text = io.StringIO(text)
        self.tio = text
        self.content_type = content_type
        self.content_length = content_length
