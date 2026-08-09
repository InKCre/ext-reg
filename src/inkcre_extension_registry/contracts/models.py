from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from semantic_version import NpmSpec, Version

SEGMENT_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
TARGET_KEY_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
KNOWN_CONDITION_KEYS = frozenset(
    {
        "inkcre.integration",
        "inkcre.extension-api",
        "module-federation.runtime",
        "module-federation.share-scope",
        "shared.vue",
        "shared.@inkcre/core",
        "web.ecmascript",
        "python",
    }
)

CoordinateSegment = Annotated[str, Field(min_length=1, max_length=64)]
TargetKey = Annotated[str, Field(min_length=1, max_length=128)]
Digest = Annotated[str, Field(pattern=DIGEST_PATTERN.pattern)]
ReleaseState = Literal["preparing", "published", "yanked", "blocked"]
ConditionOperator = Literal["equals", "semver"]
PlatformProfile = dict[str, str]


def validate_segment(value: str) -> str:
    if not SEGMENT_PATTERN.fullmatch(value):
        raise ValueError("must be a canonical lowercase ASCII Registry segment")
    return value


def validate_version(value: str) -> str:
    if value.startswith("v") or "+" in value:
        raise ValueError("must be strict SemVer without a leading v or build metadata")
    try:
        parsed = Version(value)
    except ValueError as error:
        raise ValueError("must be strict SemVer") from error
    if str(parsed) != value:
        raise ValueError("must use canonical SemVer spelling")
    return value


def validate_target_key(value: str) -> str:
    if not TARGET_KEY_PATTERN.fullmatch(value):
        raise ValueError("must be a canonical lowercase target key")
    return value


def validate_relative_path(value: str) -> str:
    if not value or "\\" in value or "?" in value or "#" in value:
        raise ValueError("must be a non-empty URL-safe POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("must be normalized and traversal-free")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError("must use normalized POSIX spelling")
    return value


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Condition(ContractModel):
    key: str = Field(min_length=1, max_length=128)
    operator: ConditionOperator
    value: str = Field(min_length=1, max_length=256)

    @field_validator("key")
    @classmethod
    def key_is_known(cls, value: str) -> str:
        if value not in KNOWN_CONDITION_KEYS:
            raise ValueError("unknown condition key")
        return value

    @model_validator(mode="after")
    def semver_range_is_valid(self) -> Condition:
        if self.operator == "semver":
            try:
                NpmSpec(self.value)
            except ValueError as error:
                raise ValueError("invalid SemVer range") from error
        return self


class FileDescriptor(ContractModel):
    sha256: str = Field(pattern=HEX_DIGEST_PATTERN.pattern)
    size: int = Field(ge=0, le=20 * 1024 * 1024)
    media_type: str = Field(min_length=1, max_length=256)


class TargetManifest(ContractModel):
    schema_version: Literal[1] = 1
    artifact_format: str = Field(min_length=1, max_length=128)
    entrypoint: str
    conditions: tuple[Condition, ...]
    files: dict[str, FileDescriptor] = Field(min_length=1, max_length=2048)

    @field_validator("entrypoint")
    @classmethod
    def entrypoint_is_safe(cls, value: str) -> str:
        return validate_relative_path(value)

    @field_validator("files")
    @classmethod
    def file_paths_are_safe(cls, value: dict[str, FileDescriptor]) -> dict[str, FileDescriptor]:
        for path in value:
            validate_relative_path(path)
        return value

    @model_validator(mode="after")
    def contract_is_coherent(self) -> TargetManifest:
        if self.entrypoint not in self.files:
            raise ValueError("entrypoint must name one declared file")
        keys = [condition.key for condition in self.conditions]
        if len(keys) != len(set(keys)):
            raise ValueError("condition keys must be unique")
        if self.artifact_format not in {"module-federation-esm-v1", "python-bundle-v1"}:
            raise ValueError("unsupported artifact format")
        integration = next(
            (condition for condition in self.conditions if condition.key == "inkcre.integration"),
            None,
        )
        if integration is None or integration.operator != "equals":
            raise ValueError("inkcre.integration equals condition is required")
        if integration.value != self.artifact_format:
            raise ValueError("artifact format must equal inkcre.integration")
        return self

    def canonical_bytes(self) -> bytes:
        value = self.model_dump(mode="json")
        value["conditions"] = sorted(
            value["conditions"], key=lambda item: (item["key"], item["operator"], item["value"])
        )
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return f"sha256:{hashlib.sha256(self.canonical_bytes()).hexdigest()}"


class TargetPublishConfig(ContractModel):
    schema_version: Literal[1] = 1
    coordinate: str
    version: str
    target_key: TargetKey
    artifact_format: str
    entrypoint: str
    conditions: tuple[Condition, ...]

    @field_validator("coordinate")
    @classmethod
    def coordinate_is_canonical(cls, value: str) -> str:
        parts = value.split("/")
        if len(parts) != 2:
            raise ValueError("coordinate must be namespace/name")
        validate_segment(parts[0])
        validate_segment(parts[1])
        return value

    @field_validator("version")
    @classmethod
    def version_is_canonical(cls, value: str) -> str:
        return validate_version(value)

    @field_validator("target_key")
    @classmethod
    def target_key_is_canonical(cls, value: str) -> str:
        return validate_target_key(value)

    @field_validator("entrypoint")
    @classmethod
    def entrypoint_is_safe(cls, value: str) -> str:
        return validate_relative_path(value)

    @property
    def namespace(self) -> str:
        return self.coordinate.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.coordinate.split("/", 1)[1]


class TargetAssociation(ContractModel):
    manifest: TargetManifest
    source_repository: str = Field(min_length=1, max_length=512)
    source_revision: str = Field(min_length=1, max_length=128)
    build_id: str | None = Field(default=None, max_length=256)


class TargetRecord(ContractModel):
    target_key: TargetKey
    target_digest: Digest
    artifact_format: str
    entrypoint: str
    conditions: tuple[Condition, ...]
    source_repository: str | None = None
    source_revision: str | None = None
    build_id: str | None = None

    @field_validator("target_key")
    @classmethod
    def target_key_is_canonical(cls, value: str) -> str:
        return validate_target_key(value)


class ReleaseRecord(ContractModel):
    namespace: CoordinateSegment
    name: CoordinateSegment
    version: str
    state: ReleaseState
    targets: tuple[TargetRecord, ...]

    @field_validator("namespace", "name")
    @classmethod
    def segment_is_canonical(cls, value: str) -> str:
        return validate_segment(value)

    @field_validator("version")
    @classmethod
    def version_is_canonical(cls, value: str) -> str:
        return validate_version(value)


class ExtensionRecord(ContractModel):
    namespace: CoordinateSegment
    name: CoordinateSegment
    versions: tuple[ReleaseRecord, ...] = ()

    @field_validator("namespace", "name")
    @classmethod
    def segment_is_canonical(cls, value: str) -> str:
        return validate_segment(value)
