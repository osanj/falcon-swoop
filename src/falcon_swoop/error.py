# ruff: noqa: D101

class FalconSwoopError(Exception):
    pass


class FalconSwoopConfigError(FalconSwoopError):
    pass


class FalconSwoopDocGenerationError(FalconSwoopError):
    pass


class FalconSwoopWarning(Warning):
    pass


class FalconSwoopConfigWarning(FalconSwoopWarning):
    pass
