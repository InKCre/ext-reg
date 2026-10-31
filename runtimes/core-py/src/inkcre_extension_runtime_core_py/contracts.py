"""Names used by the Runtime over generated Registry contract consumers."""

from pydantic import model_validator

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
    Distribution,
    ReleaseRecord,
)
from .generated.registry import (
    NativeReleaseRecord as GeneratedNativeReleaseRecord,
)
from .generated.registry import (
    PythonDistribution as PythonReleaseDescriptor,
)
from .generated.registry import (
    PythonEntryPoint as EntryPointDescriptor,
)
from .generated.registry import (
    State as ReleaseState,
)


class ExtensionReleaseDescriptor(ReleaseRecord):
    """Preserve the flat Runtime API over generated discriminated wire variants."""

    distribution: Distribution

    @model_validator(mode="after")
    def native_association_is_valid(self) -> "ExtensionReleaseDescriptor":
        GeneratedNativeReleaseRecord.model_validate(self.model_dump(mode="json"))
        return self


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
