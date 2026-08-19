"""Canonical public Registry contract models and semantic validators."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator
from semantic_version import NpmSpec, Version

SEGMENT_PATTERN_TEXT = r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$"
EXTENSION_NAME_PATTERN_TEXT = (
    r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$"
)
STRICT_SEMVER_PATTERN_TEXT = (
    r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?:(?:0|[1-9][0-9]*)|(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))"
    r"(?:\.(?:(?:0|[1-9][0-9]*)|(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)))*)?$"
)
SEGMENT_PATTERN = re.compile(SEGMENT_PATTERN_TEXT)
EXTENSION_NAME_PATTERN = re.compile(EXTENSION_NAME_PATTERN_TEXT)
STRICT_SEMVER_PATTERN = re.compile(STRICT_SEMVER_PATTERN_TEXT)
PROJECT_PATTERN_TEXT = r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,198}[A-Za-z0-9])?$"
ENTRY_GROUP_PATTERN_TEXT = r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
ENTRY_NAME_PATTERN_TEXT = ENTRY_GROUP_PATTERN_TEXT
ENTRY_OBJECT_PATTERN_TEXT = r"^[A-Za-z_][A-Za-z0-9_.]*(?::[A-Za-z_][A-Za-z0-9_.]*)?$"
PROJECT_PATTERN = re.compile(PROJECT_PATTERN_TEXT)
NORMALIZED_PROJECT_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,198}[a-z0-9])?$")
ENTRY_GROUP_PATTERN = re.compile(ENTRY_GROUP_PATTERN_TEXT)
ENTRY_NAME_PATTERN = re.compile(ENTRY_NAME_PATTERN_TEXT)
ENTRY_OBJECT_PATTERN = re.compile(ENTRY_OBJECT_PATTERN_TEXT)
HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_NORMALIZER = re.compile(r"[-_.]+")

ReleaseState = Literal["preparing", "published", "yanked", "blocked"]


def validate_segment(value: str) -> str:
    if not SEGMENT_PATTERN.fullmatch(value):
        raise ValueError("must be a canonical lowercase ASCII Registry segment")
    return value


def validate_version(value: str) -> str:
    if len(value) > 128 or not STRICT_SEMVER_PATTERN.fullmatch(value):
        raise ValueError("must be strict SemVer without a leading v or build metadata")
    try:
        parsed = Version(value)
    except ValueError as error:
        raise ValueError("must be strict SemVer") from error
    if str(parsed) != value:
        raise ValueError("must use canonical SemVer spelling")
    return value


def validate_extension_name(value: str) -> str:
    if len(value) > 129 or not EXTENSION_NAME_PATTERN.fullmatch(value):
        raise ValueError("must be canonical namespace/name")
    namespace, name = value.split("/", 1)
    validate_segment(namespace)
    validate_segment(name)
    return value


RegistrySegment = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=SEGMENT_PATTERN_TEXT),
    AfterValidator(validate_segment),
]
CanonicalExtensionName = Annotated[
    str,
    Field(min_length=3, max_length=129, pattern=EXTENSION_NAME_PATTERN_TEXT),
    AfterValidator(validate_extension_name),
]
StrictSemVer = Annotated[
    str,
    Field(min_length=5, max_length=128, pattern=STRICT_SEMVER_PATTERN_TEXT),
    AfterValidator(validate_version),
]


def python_project_version(value: str) -> str:
    """Return the one lossless PEP 440 spelling admitted for a product Release."""

    validate_version(value)
    parsed = Version(value)
    base = f"{parsed.major}.{parsed.minor}.{parsed.patch}"
    if not parsed.prerelease:
        return base
    if (
        len(parsed.prerelease) != 2
        or parsed.prerelease[0] not in {"a", "b", "rc"}
        or not parsed.prerelease[1].isdigit()
    ):
        raise ValueError(
            "Python Releases support only lossless SemVer a.N, b.N, or rc.N pre-releases"
        )
    return f"{base}{parsed.prerelease[0]}{parsed.prerelease[1]}"


def normalize_project_name(value: str) -> str:
    if not PROJECT_PATTERN.fullmatch(value):
        raise ValueError("must be a valid Python Project name")
    normalized = _PROJECT_NORMALIZER.sub("-", value).lower()
    if not NORMALIZED_PROJECT_PATTERN.fullmatch(normalized):
        raise ValueError("must normalize to a valid Python Project name")
    return normalized


def validate_host_sdk_range(value: str) -> str:
    try:
        # Host SDK ranges are one language-neutral contract. Native package
        # syntaxes such as PEP 440 comma conjunctions are deliberately rejected.
        NpmSpec(value)
    except ValueError as error:
        raise ValueError("must be a valid SemVer range") from error
    return value


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PythonEntryPoint(ContractModel):
    group: str = Field(min_length=1, max_length=128, pattern=ENTRY_GROUP_PATTERN_TEXT)
    name: str = Field(min_length=1, max_length=128, pattern=ENTRY_NAME_PATTERN_TEXT)
    object: str = Field(min_length=1, max_length=256, pattern=ENTRY_OBJECT_PATTERN_TEXT)

    @field_validator("group")
    @classmethod
    def group_is_valid(cls, value: str) -> str:
        if not ENTRY_GROUP_PATTERN.fullmatch(value):
            raise ValueError("must be a valid entry-point group")
        return value

    @field_validator("name")
    @classmethod
    def name_is_valid(cls, value: str) -> str:
        if not ENTRY_NAME_PATTERN.fullmatch(value):
            raise ValueError("must be a valid entry-point name")
        return value

    @field_validator("object")
    @classmethod
    def object_is_valid(cls, value: str) -> str:
        if not ENTRY_OBJECT_PATTERN.fullmatch(value):
            raise ValueError("must be a module or module:attribute reference")
        return value


class PythonAssociationInput(ContractModel):
    project: str = Field(min_length=1, max_length=200, pattern=PROJECT_PATTERN_TEXT)
    host_sdk: Literal["core-py"]
    host_sdk_version: str = Field(min_length=1, max_length=256)
    entry_point: PythonEntryPoint
    source_repository: str = Field(min_length=1, max_length=512)
    source_revision: str = Field(min_length=1, max_length=128)
    build_id: str | None = Field(default=None, min_length=1, max_length=256)

    @field_validator("project")
    @classmethod
    def project_is_valid(cls, value: str) -> str:
        normalize_project_name(value)
        return value

    @field_validator("host_sdk_version")
    @classmethod
    def range_is_valid(cls, value: str) -> str:
        return validate_host_sdk_range(value)


class ModuleFederationAssociationInput(ContractModel):
    host_sdk: Literal["@inkcre/core"]
    host_sdk_version: str = Field(min_length=1, max_length=256)
    source_repository: str = Field(min_length=1, max_length=512)
    source_revision: str = Field(min_length=1, max_length=128)
    build_id: str | None = Field(default=None, min_length=1, max_length=256)

    @field_validator("host_sdk_version")
    @classmethod
    def range_is_valid(cls, value: str) -> str:
        return validate_host_sdk_range(value)


class PrepareReleaseRequest(ContractModel):
    nickname: str = Field(min_length=1, max_length=128)
    version: StrictSemVer
    python: PythonAssociationInput | None = None
    module_federation: ModuleFederationAssociationInput | None = None

    @model_validator(mode="after")
    def association_is_declared(self) -> PrepareReleaseRequest:
        if self.python is None and self.module_federation is None:
            raise ValueError("at least one native Distribution association is required")
        if self.python is not None:
            python_project_version(self.version)
        return self


class PythonDistribution(ContractModel):
    project: str = Field(pattern=PROJECT_PATTERN_TEXT)
    simple_url: str
    host_sdk: Literal["core-py"]
    host_sdk_version: str
    entry_point: PythonEntryPoint


class ModuleFederationDistribution(ContractModel):
    manifest_url: str
    host_sdk: Literal["@inkcre/core"]
    host_sdk_version: str


class ReleaseRecord(ContractModel):
    name: CanonicalExtensionName
    nickname: str
    version: StrictSemVer
    state: ReleaseState
    python: PythonDistribution | None = None
    module_federation: ModuleFederationDistribution | None = None


class ExtensionSummary(ContractModel):
    name: CanonicalExtensionName
    nickname: str


class ExtensionRecord(ContractModel):
    name: CanonicalExtensionName
    nickname: str
    releases: tuple[ReleaseRecord, ...] = ()


class YankRequest(ContractModel):
    reason: str = Field(default="Yanked by publisher", min_length=1, max_length=400)


class InstalledHostSdk(ContractModel):
    name: Literal["core-py"]
    version: str = Field(min_length=1, max_length=256)

    @field_validator("version")
    @classmethod
    def range_is_valid(cls, value: str) -> str:
        return validate_host_sdk_range(value)


class InstalledPythonDistribution(ContractModel):
    project: str = Field(min_length=1, max_length=200, pattern=PROJECT_PATTERN_TEXT)
    project_version: str = Field(min_length=1, max_length=128)
    entry_point: PythonEntryPoint

    @field_validator("project")
    @classmethod
    def project_is_valid(cls, value: str) -> str:
        normalize_project_name(value)
        return value


class InstalledExtension(ContractModel):
    schema_version: Literal[1]
    name: CanonicalExtensionName
    version: StrictSemVer
    host_sdk: InstalledHostSdk
    python: InstalledPythonDistribution

    @model_validator(mode="after")
    def python_version_matches_release(self) -> InstalledExtension:
        if self.python.project_version != python_project_version(self.version):
            raise ValueError("Python Project version must match the Release version")
        return self


class PythonConsumerContracts(ContractModel):
    """Schema-only root used to generate Python consumer bindings."""

    extension: ExtensionRecord
    extension_summary: ExtensionSummary
    prepare_release: PrepareReleaseRequest
    release: ReleaseRecord
    yank: YankRequest
