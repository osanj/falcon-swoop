from falcon_api import ApiBaseResource, operation, ApiQueryParam
from pydantic import BaseModel, Field
import falcon
import falcon.testing


class NewUserInput(BaseModel):
    firstname: str
    lastname: str


class NewUserOutput(BaseModel):
    id: int


class UserResource(ApiBaseResource):

    def __init__(self):
        super().__init__("/user")

    @operation(method="POST")
    def create_new_user(
        self,
        user_input: NewUserInput,
        offset: int = ApiQueryParam(ge=1),
    ) -> NewUserOutput:
        print(user_input)
        return NewUserOutput(id=5)


def dev() -> None:
    ur = UserResource()
    app = falcon.App()
    app.add_route(ur.route, ur)

    test_client = falcon.testing.TestClient(app)
    resp = test_client.simulate_post(ur.route, json={"firstname": "John", "lastname": "Doe"})
    print(resp.status)
    print(resp.text)


if __name__ == "__main__":
    dev()
