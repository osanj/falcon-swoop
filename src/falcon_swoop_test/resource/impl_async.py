from typing import Any, Literal

import falcon

from falcon_swoop import (
    ApiBaseResource,
    OpAsgiContext,
    OpOutput,
    operation,
    query_param,
    header_param,
    operation_doc,
    HttpBinary,
    HttpText,
    path_param,
)
from falcon_swoop_test.resource.common import WeatherLevel, BasicInput, BasicOutput, country_param, city_id_param


class BasicResource1(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/basic")

    @operation(method="GET")
    async def get_something(
        self,
        limit: int = query_param(default=10, ge=1, le=20),
        offset: int = query_param(ge=0),
    ) -> BasicOutput:
        return BasicOutput(data={"limit": limit, "offset": offset})

    @operation(method="POST")
    async def post_something(self, basic_input: BasicInput, ctx: OpAsgiContext) -> BasicOutput:
        content_type = ctx.req.content_type
        return BasicOutput(data={"param1": basic_input.param1, "content_type": content_type})


class BasicResource2(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/country/{country}/city/{cityId}")

    @operation(method="GET")
    async def get_city_data(
        self,
        country: str = country_param,
        city_id: int = city_id_param,
        api_key: str = header_param(default="dummy", alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"country": country, "city": city_id, "api_key": api_key})

    @operation(method="PUT", default_status=201)
    async def put_city_data(
        self,
        req: BasicInput | None,
        country: str = country_param,
        city_id: int = city_id_param,
        tag: str | None = query_param(),
        api_key: str | None = header_param(alias="X-API-KEY"),
    ) -> BasicOutput:
        return BasicOutput(data={"tag": tag, "api_key": api_key, "param1": None if req is None else req.param1})

    @operation_doc(operation_id="updateCityData", deprecated=True)
    async def on_patch(self, req: falcon.Request, resp: falcon.Response, **params: Any) -> None:
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "patched"

    async def on_delete(self, req: falcon.Request, resp: falcon.Response, **params: Any) -> None:
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "deleted"


class BasicResource3(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/weather")

    @operation(method="GET")
    async def get_weather(
        self,
        mode: WeatherLevel = query_param(default=WeatherLevel.LOCAL),
        unit: Literal["C", "F"] = query_param(default="C"),
    ) -> BasicOutput:
        return BasicOutput(data={"temperature": 20, "mode": mode.name, "unit": unit})

    @operation(method="PUT")
    async def add_weather_sample(
        self,
        sample: BasicInput,
        transient: bool = query_param(default=True),
    ) -> OpOutput[BasicOutput]:
        payload = BasicOutput(data={"param1": sample.param1, "transient": transient})
        return OpOutput(
            payload=payload,
            status_code=200 if transient else 201,
        )


class BasicResource4(ApiBaseResource):

    def __init__(self) -> None:
        super().__init__("/blob/{blobId}")

    @operation(method="GET")
    async def get_blob(
        self,
        blob_id: str = path_param(alias="blobId"),
    ) -> HttpBinary:
        return HttpBinary(binary=b"blob" + blob_id.encode())

    @operation(method="POST")
    async def add_blob(
        self,
        blob: HttpBinary,
        blob_id: str = path_param(alias="blobId"),
    ) -> BasicOutput:
        data = blob.bio.read()
        output = BasicOutput(
            data={
                "data": data.decode(),
                "content_length": blob.content_length,
                "content_type": blob.content_type,
            }
        )
        return output

    @operation(method="PATCH")
    async def get_blob_stats(
        self,
        blob_id: str = path_param(alias="blobId"),
    ) -> HttpText:
        return HttpText(text="stat;count\nsize;12345\naccesses;123", content_type="text/csv")

    @operation(method="PUT")
    async def add_blob_stats(
        self,
        stats: HttpText,
        blob_id: str = path_param(alias="blobId"),
    ) -> BasicOutput:
        text = stats.tio.read()
        output = BasicOutput(
            data={
                "data": text,
                "content_length": stats.content_length,
                "content_type": stats.content_type,
            }
        )
        return output
