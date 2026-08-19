"""Public Extension-facing and Core Host-facing Runtime API."""

import typing

from .base import EmptyConfig, EmptyState, ExtensionBase
from .errors import (
    ExtensionAcquisitionError,
    ExtensionCompatibilityError,
    ExtensionEntryPointError,
    ExtensionLifecycleError,
    ExtensionNotInstalledError,
    ExtensionRegistryError,
    ExtensionRestartRequiredError,
    ExtensionRuntimeError,
    ExtensionStateConflictError,
)
from .manager import ExtensionManager, RunningExtension

if typing.TYPE_CHECKING:
    from .publication import PublicHTTPRoute

__all__ = [
    "EmptyConfig",
    "EmptyState",
    "ExtensionAcquisitionError",
    "ExtensionBase",
    "ExtensionCompatibilityError",
    "ExtensionEntryPointError",
    "ExtensionLifecycleError",
    "ExtensionManager",
    "ExtensionNotInstalledError",
    "ExtensionRegistryError",
    "ExtensionRestartRequiredError",
    "ExtensionRuntimeError",
    "ExtensionStateConflictError",
    "PublicHTTPRoute",
    "RunningExtension",
]


def __getattr__(name: str):
    if name == "PublicHTTPRoute":
        from .publication import PublicHTTPRoute

        return PublicHTTPRoute
    raise AttributeError(name)
