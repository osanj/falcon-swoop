from enum import unique, Enum
from typing import Any

from pydantic import BaseModel

from falcon_swoop import path_param


@unique
class WeatherLevel(str, Enum):
    LOCAL = "LOCAL"
    REGIONAL = "REGIONAL"
    GLOBAL = "GLOBAL"


class BasicInput(BaseModel):
    param1: str


class BasicOutput(BaseModel):
    data: dict[str, Any]


country_param = path_param(pattern=r"^[A-Z]{2}$")
city_id_param = path_param(alias="cityId", ge=1)
