from typing import Any, Sequence

from falcon_swoop.error import FalconSwoopConfigError


class ApiRoute:

    def __init__(self, plain: str):
        self.plain = plain.strip().rstrip("/")
        self.parts = plain.strip("/").split("/")
        param_names = self.find_param_names(self.parts)
        self.param_names = set(param_names)
        if len(param_names) != len(self.param_names):
            raise FalconSwoopConfigError(f"Duplicate parameters were found in route {plain}")

    @classmethod
    def find_param_names(cls, parts: Sequence[str]) -> Sequence[str]:
        names = []
        for p in parts:
            if p.startswith("{") and p.endswith("}"):
                names.append(p[1:-1])
        return names

    def format(self, **kwargs: Any) -> str:
        keys_actual = set(kwargs.keys())
        keys_expected = set(self.param_names)
        if keys_actual != keys_expected:
            raise ValueError(f"Expected values for {keys_expected}, but got {keys_actual}")
        str_parts = []
        for p in self.parts:
            if p.startswith("{") and p.endswith("}"):
                name = p[1:-1]
                value = str(kwargs[name])
                str_parts.append(value)
            else:
                str_parts.append(p)
        return "/" + "/".join(str_parts)
