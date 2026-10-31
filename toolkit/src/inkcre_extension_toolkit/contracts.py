"""Generated public models plus native semantic contract helpers."""

from typing import Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator

from inkcre_extension_toolkit.generated.contracts import (
    ExtensionRecord,
    ExtensionSummary,
    ModuleFederationAssociationInput,
    ModuleFederationDistribution,
    PythonAssociationInput,
    PythonDistribution,
    ReleaseRecord,
    YankRequest,
)
from inkcre_extension_toolkit.generated.contracts import (
    NativePrepareReleaseRequest as GeneratedNativePrepareReleaseRequest,
)
from inkcre_extension_toolkit.generated.contracts import (
    NativeReleaseRecord as GeneratedNativeReleaseRecord,
)
from inkcre_extension_toolkit.generated.contracts import (
    PrepareReleaseRequest as GeneratedPrepareReleaseRequest,
)
from inkcre_extension_toolkit.generated.contracts import (
    PythonEntryPoint as GeneratedPythonEntryPoint,
)
from inkcre_extension_toolkit.generated.installed_extension import (
    InstalledExtension,
    InstalledHostSdk,
    InstalledPythonDistribution,
)
from inkcre_extension_toolkit.semantic import (
    CanonicalExtensionName,
    ContractModel,
    RegistrySegment,
    ReleaseState,
    StrictSemVer,
    normalize_project_name,
    python_project_version,
    validate_extension_name,
    validate_host_sdk_range,
    validate_segment,
    validate_version,
)


class PythonEntryPoint(GeneratedPythonEntryPoint):
    @field_validator("group", "name", "object")
    @classmethod
    def entry_point_part_is_valid(cls, value: str, info: ValidationInfo) -> str:
        from inkcre_extension_toolkit.semantic import validate_entry_point_part

        assert info.field_name is not None
        return validate_entry_point_part(value, field_name=info.field_name)


class PrepareReleaseRequest(GeneratedPrepareReleaseRequest):
    @model_validator(mode="after")
    def association_is_declared(self) -> "PrepareReleaseRequest":
        if self.python is None and self.module_federation is None:
            raise ValueError("at least one native Distribution association is required")
        if self.python is not None:
            python_project_version(self.version)
            normalize_project_name(self.python.project)
            validate_host_sdk_range(self.python.host_sdk_version)
            PythonEntryPoint.model_validate(self.python.entry_point.model_dump(mode="json"))
        if self.module_federation is not None:
            validate_host_sdk_range(self.module_federation.host_sdk_version)
        return self


class NativePrepareReleaseRequest(PrepareReleaseRequest):
    """Keep the flat public API while delegating native shape to the generated union."""

    @model_validator(mode="after")
    def native_association_is_valid(self) -> "NativePrepareReleaseRequest":
        GeneratedNativePrepareReleaseRequest.model_validate(self.model_dump(mode="json"))
        return self


class NativeReleaseRecord(ReleaseRecord):
    distribution: Literal["python", "module_federation"]

    @model_validator(mode="after")
    def native_association_is_valid(self) -> "NativeReleaseRecord":
        GeneratedNativeReleaseRecord.model_validate(self.model_dump(mode="json"))
        return self


class NativeExtensionRecord(ExtensionSummary):
    releases: list[NativeReleaseRecord] = Field(default_factory=list)


__all__ = [
    "CanonicalExtensionName",
    "ContractModel",
    "ExtensionRecord",
    "ExtensionSummary",
    "InstalledExtension",
    "InstalledHostSdk",
    "InstalledPythonDistribution",
    "ModuleFederationAssociationInput",
    "ModuleFederationDistribution",
    "NativeExtensionRecord",
    "NativePrepareReleaseRequest",
    "NativeReleaseRecord",
    "PrepareReleaseRequest",
    "PythonAssociationInput",
    "PythonDistribution",
    "PythonEntryPoint",
    "RegistrySegment",
    "ReleaseRecord",
    "ReleaseState",
    "StrictSemVer",
    "YankRequest",
    "normalize_project_name",
    "python_project_version",
    "validate_extension_name",
    "validate_host_sdk_range",
    "validate_segment",
    "validate_version",
]
