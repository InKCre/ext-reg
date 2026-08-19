"""Generated public models plus native semantic contract helpers."""

from pydantic import ValidationInfo, field_validator, model_validator

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
