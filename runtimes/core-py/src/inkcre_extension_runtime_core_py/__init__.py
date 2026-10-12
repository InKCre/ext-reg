"""Public Extension-facing and Core Host-facing Runtime API."""

import typing

from .base import EmptyConfig, EmptyState, ExtensionBase
from .errors import (
    ExtensionAcquisitionError,
    ExtensionCompatibilityError,
    ExtensionEntryPointError,
    ExtensionLifecycleError,
    ExtensionNativeSupportChangeError,
    ExtensionNotInstalledError,
    ExtensionRegistryError,
    ExtensionReleaseUnavailableError,
    ExtensionRuntimeError,
    ExtensionStateConflictError,
)
from .manager import ExtensionManager, RunningExtension
from .support import NativeDistributionFormat, require_native_support_preserved

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
    "ExtensionNativeSupportChangeError",
    "ExtensionNotInstalledError",
    "ExtensionRegistryError",
    "ExtensionReleaseUnavailableError",
    "ExtensionRuntimeError",
    "ExtensionStateConflictError",
    "NativeDistributionFormat",
    "PublicHTTPRoute",
    "RunningExtension",
    "require_native_support_preserved",
]


def __getattr__(name: str):
    if name == "PublicHTTPRoute":
        from .publication import PublicHTTPRoute

        return PublicHTTPRoute
    raise AttributeError(name)
