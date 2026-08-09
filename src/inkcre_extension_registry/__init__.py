"""InKCre Extension Registry contracts, clients, and service."""

from .contracts.compatibility import select_compatible_target, target_matches
from .contracts.lifecycle import ExtensionLifecycle, ExtensionState
from .contracts.models import (
    Condition,
    FileDescriptor,
    PlatformProfile,
    ReleaseRecord,
    TargetManifest,
    TargetRecord,
)

__all__ = [
    "Condition",
    "ExtensionLifecycle",
    "ExtensionState",
    "FileDescriptor",
    "PlatformProfile",
    "ReleaseRecord",
    "TargetManifest",
    "TargetRecord",
    "select_compatible_target",
    "target_matches",
]

__version__ = "0.1.0"
