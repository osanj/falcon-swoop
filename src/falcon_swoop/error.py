# ruff: noqa: D101


class SwoopError(Exception):
    pass


class SwoopConfigError(SwoopError):
    pass


class SwoopDocGenerationError(SwoopError):
    pass


class SwoopWarning(Warning):
    pass


class SwoopConfigWarning(SwoopWarning):
    pass
