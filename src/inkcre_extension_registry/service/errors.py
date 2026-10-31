"""Expected Registry failures, independent of persistence and HTTP adapters."""


class RegistryConflictError(RuntimeError):
    pass


class RegistryNotFoundError(RuntimeError):
    pass


class RegistryStateError(RuntimeError):
    pass


class RegistryBlockedError(RegistryStateError):
    pass
