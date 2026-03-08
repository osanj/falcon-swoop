import falcon

from falcon_swoop import OpResponseDoc, header_param

# using shared header param for consistency
# setting default value, so falcon-swoop does not complain about missing secret header
ADMIN_SECRET_HDR = header_param(alias="x-admin-secret", default=None)
DOC_UNAUTHORIZED = OpResponseDoc("Missing or incorrect admin secret")


class AdminSecretVerification:
    def __init__(self, secret: str):
        self.secret = secret

    def verify(self, secret: str) -> None:
        if secret != self.secret:
            raise falcon.HTTPUnauthorized()
