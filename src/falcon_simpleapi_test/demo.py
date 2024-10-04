from falcon_simpleapi.resource import BaseResource, operation
from pydantic import BaseModel
import falcon
import falcon.testing


class NewUserInput(BaseModel):
    firstname: str
    lastname: str


class NewUserOutput(BaseModel):
    id: int


class UserResource(BaseResource):

    def __init__(self):
        super().__init__("/user")

    @operation(method="POST")
    def create_new_user(self, user_input: NewUserInput, q_name) -> NewUserOutput:
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
