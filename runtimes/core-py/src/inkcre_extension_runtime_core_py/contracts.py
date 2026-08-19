"""Names used by the Runtime over generated Registry contract consumers."""

from .generated.installed import (
    InstalledExtension as InstalledExtensionRecord,
)
from .generated.installed import (
    InstalledHostSdk as InstalledHostSDK,
)
from .generated.installed import (
    InstalledPythonDistribution,
)
from .generated.installed import (
    PythonEntryPoint as InstalledEntryPointDescriptor,
)
from .generated.registry import (
    PythonDistribution as PythonReleaseDescriptor,
)
from .generated.registry import (
    PythonEntryPoint as EntryPointDescriptor,
)
from .generated.registry import (
    ReleaseRecord as ExtensionReleaseDescriptor,
)
from .generated.registry import (
    State as ReleaseState,
)

__all__ = [
    "EntryPointDescriptor",
    "ExtensionReleaseDescriptor",
    "InstalledEntryPointDescriptor",
    "InstalledExtensionRecord",
    "InstalledHostSDK",
    "InstalledPythonDistribution",
    "PythonReleaseDescriptor",
    "ReleaseState",
]
