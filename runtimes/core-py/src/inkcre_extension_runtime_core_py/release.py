"""Exact Release resolution and Core Host compatibility validation."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

import pydantic
import requests
from packaging.utils import canonicalize_name
from semantic_version import NpmSpec, Version

from .contracts import ExtensionReleaseDescriptor, PythonReleaseDescriptor
from .errors import ExtensionCompatibilityError, ExtensionRegistryError

CORE_HOST_SDK = "core-py"
ENTRY_POINT_GROUP = "inkcre.core.extensions"
_SEGMENT = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?$"
)


def validate_coordinate(name: str, version: str | None = None) -> tuple[str, str]:
    parts = name.split("/")
    if len(parts) != 2 or any(_SEGMENT.fullmatch(part) is None for part in parts):
        raise ExtensionCompatibilityError("Extension name is not canonical")
    if version is not None and _SEMVER.fullmatch(version) is None:
        raise ExtensionCompatibilityError("Extension version is not strict SemVer")
    return parts[0], parts[1]


class RegistryReleaseClient:
    def __init__(self, origin: str, timeout: float = 10.0) -> None:
        configured = _configured_origin(origin)
        self.origin = urlunsplit((configured.scheme, configured.netloc, "/", "", ""))
        self.timeout = timeout

    def get(self, name: str, version: str) -> ExtensionReleaseDescriptor:
        namespace, extension = validate_coordinate(name, version)
        url = urljoin(self.origin, f"v1/extensions/{namespace}/{extension}/releases/{version}")
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            release = ExtensionReleaseDescriptor.model_validate(response.json())
        except (requests.RequestException, ValueError, pydantic.ValidationError) as error:
            raise ExtensionRegistryError(f"Registry could not resolve {name}@{version}") from error
        if (release.name, release.version) != (name, version):
            raise ExtensionRegistryError("Registry returned a different exact Release")
        return release


def require_python_association(
    release: ExtensionReleaseDescriptor,
    host_version: str,
) -> PythonReleaseDescriptor:
    association = release.python
    if association is None:
        raise ExtensionCompatibilityError("Release has no Core Python Distribution")
    _validate_host(association.host_sdk, association.host_sdk_version, host_version)
    _validate_entry_point(
        association.entry_point.group, association.entry_point.name, association.entry_point.object
    )
    return association


def _validate_host(name: str, requirement: str, host_version: str) -> None:
    if name != CORE_HOST_SDK:
        raise ExtensionCompatibilityError("Distribution targets another Host SDK")
    try:
        compatible = NpmSpec(requirement).match(Version(host_version))
    except ValueError as error:
        raise ExtensionCompatibilityError("Invalid Core Host SDK range") from error
    if not compatible:
        raise ExtensionCompatibilityError(f"Distribution does not support core-py@{host_version}")


def _validate_entry_point(group: str, name: str, object_: str) -> None:
    if group != ENTRY_POINT_GROUP or not name or ":" not in object_:
        raise ExtensionCompatibilityError("Python Distribution entry point is invalid")


def simple_project_and_index_urls(
    origin: str,
    association: PythonReleaseDescriptor,
) -> tuple[str, str]:
    configured = _configured_origin(origin)
    project = urlsplit(urljoin(origin.rstrip("/") + "/", association.simple_url))
    if (project.scheme, project.netloc.lower()) != (configured.scheme, configured.netloc.lower()):
        raise ExtensionCompatibilityError("Registry Simple URL is not same-origin")
    if any((project.username, project.password, project.query, project.fragment)):
        raise ExtensionCompatibilityError("Registry Simple URL is invalid")
    expected = f"/simple/{canonicalize_name(association.project)}/"
    if project.path != expected:
        raise ExtensionCompatibilityError("Registry Simple URL has the wrong Project path")
    project_url = urlunsplit(project)
    return project_url, urlunsplit((project.scheme, project.netloc, "/simple/", "", ""))


def _configured_origin(origin: str):
    configured = urlsplit(origin)
    if configured.scheme not in {"http", "https"} or not configured.netloc:
        raise ExtensionCompatibilityError("Configured Registry origin is invalid")
    if (
        configured.username is not None
        or configured.password is not None
        or configured.path not in {"", "/"}
        or configured.query
        or configured.fragment
    ):
        raise ExtensionCompatibilityError("Configured Registry origin must be a bare HTTP origin")
    return configured
