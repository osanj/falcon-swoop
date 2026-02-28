from dataclasses import dataclass

import falcon.asgi


@dataclass
class OpContext:
    req: falcon.Request
    resp: falcon.Response


@dataclass
class OpAsgiContext:
    req: falcon.asgi.Request
    resp: falcon.asgi.Response
