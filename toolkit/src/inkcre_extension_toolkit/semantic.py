"""Native semantic checks that JSON Schema cannot express completely."""

from __future__ import annotations

from typing import Annotated, Literal

from packaging.utils import InvalidName, canonicalize_name
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from semantic_version import NpmSpec, Version

from inkcre_extension_toolkit.generated.contracts import (
    ExtensionSummary as GeneratedExtensionSummary,
)
from inkcre_extension_toolkit.generated.contracts import (
    PythonEntryPoint as GeneratedPythonEntryPoint,
)

ReleaseState = Literal["preparing", "published", "yanked", "blocked"]


def validate_segment(value: str) -> str:
    GeneratedExtensionSummary(name=f"{value}/x", nickname="x")
    return value


def validate_extension_name(value: str) -> str:
    GeneratedExtensionSummary(name=value, nickname="x")
    return value


def validate_version(value: str) -> str:
    try:
        parsed = Version(value)
    except ValueError as error:
        raise ValueError("must be strict SemVer") from error
    if parsed.build or str(parsed) != value:
        raise ValueError("must use canonical SemVer spelling")
    return value


def python_project_version(value: str) -> str:
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
    try:
        normalized = canonicalize_name(value, validate=True)
    except InvalidName as error:
        raise ValueError("must be a valid Python Project name") from error
    if len(value) > 200:
        raise ValueError("must be a valid Python Project name")
    return normalized


def validate_host_sdk_range(value: str) -> str:
    try:
        NpmSpec(value)
    except ValueError as error:
        raise ValueError("must be a valid SemVer range") from error
    return value


def validate_entry_point_part(value: str, *, field_name: str) -> str:
    values = {"group": "group", "name": "name", "object": "module:object"}
    values[field_name] = value
    GeneratedPythonEntryPoint.model_validate(values)
    return value


RegistrySegment = Annotated[
    str, Field(min_length=1, max_length=64), AfterValidator(validate_segment)
]
CanonicalExtensionName = Annotated[str, AfterValidator(validate_extension_name)]
StrictSemVer = Annotated[str, AfterValidator(validate_version)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
