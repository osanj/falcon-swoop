from dataclasses import dataclass

import falcon.asgi


@dataclass
class OpContext:
    """Utility class for direct access to falcon data structures if needed.

    This context will be injected to the function decorated with ``@operation`` as argument that hints this type.
    Note that it can only be used in synchronous operations.
    """

    req: falcon.Request
    resp: falcon.Response


@dataclass
class OpAsgiContext:
    """Utility class for direct access to falcon async data structures if needed.

    This context will be injected to the function decorated with ``@operation`` as argument that hints this type.
    Note that it can only be used in asynchronous operations.
    """

    req: falcon.asgi.Request
    resp: falcon.asgi.Response
