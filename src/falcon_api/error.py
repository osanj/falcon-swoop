class FalconApiError(Exception):
    pass


class FalconApiConfigError(FalconApiError):
    pass


class FalconApiDocGenerationError(FalconApiError):
    pass
