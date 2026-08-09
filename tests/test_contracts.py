from __future__ import annotations

import hashlib

import httpx
import pytest
from pydantic import ValidationError

from inkcre_extension_registry.client import RegistryClient, RegistryReleaseStateError
from inkcre_extension_registry.contracts.compatibility import (
    select_compatible_target,
    target_matches,
)
from inkcre_extension_registry.contracts.lifecycle import ExtensionLifecycle, ExtensionState
from inkcre_extension_registry.contracts.models import (
    Condition,
    FileDescriptor,
    TargetManifest,
    TargetRecord,
    validate_version,
)


def _manifest(*conditions: Condition) -> TargetManifest:
    content = b"export default {}\n"
    return TargetManifest(
        artifact_format="module-federation-esm-v1",
        entrypoint="remoteEntry.js",
        conditions=conditions,
        files={
            "remoteEntry.js": FileDescriptor(
                sha256=hashlib.sha256(content).hexdigest(),
                size=len(content),
                media_type="text/javascript",
            )
        },
    )


def test_manifest_digest_is_canonical_and_accepts_scoped_shared_module_key() -> None:
    integration = Condition(
        key="inkcre.integration",
        operator="equals",
        value="module-federation-esm-v1",
    )
    core = Condition(key="shared.@inkcre/core", operator="semver", value="^2.0.0")

    first = _manifest(integration, core)
    second = _manifest(core, integration)

    assert first.digest == second.digest
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "01.2.3", "1.2.3+build"])
def test_product_version_rejects_noncanonical_semver(version: str) -> None:
    with pytest.raises(ValueError):
        validate_version(version)


def test_manifest_rejects_unknown_conditions_and_traversal() -> None:
    with pytest.raises(ValidationError, match="unknown condition key"):
        Condition(key="producer.private-guess", operator="equals", value="yes")

    with pytest.raises(ValidationError, match="invalid SemVer range"):
        Condition(key="python", operator="semver", value="definitely-not-a-range")

    with pytest.raises(ValidationError, match="traversal-free"):
        TargetManifest(
            artifact_format="python-bundle-v1",
            entrypoint="../extension.zip",
            conditions=(
                Condition(
                    key="inkcre.integration",
                    operator="equals",
                    value="python-bundle-v1",
                ),
            ),
            files={
                "../extension.zip": FileDescriptor(
                    sha256="0" * 64,
                    size=0,
                    media_type="application/zip",
                )
            },
        )


def test_compatibility_is_fail_closed_and_selection_is_deterministic() -> None:
    conditions = (
        Condition(key="inkcre.integration", operator="equals", value="python-bundle-v1"),
        Condition(key="python", operator="semver", value=">=3.12.0 <3.13.0"),
        Condition(key="inkcre.extension-api", operator="semver", value="^2.0.0"),
    )
    later = TargetRecord(
        target_key="python.z",
        target_digest=f"sha256:{'1' * 64}",
        artifact_format="python-bundle-v1",
        entrypoint="extension.zip",
        conditions=conditions,
    )
    earlier = later.model_copy(
        update={"target_key": "python.a", "target_digest": f"sha256:{'2' * 64}"}
    )
    compatible_profile = {
        "inkcre.integration": "python-bundle-v1",
        "python": "3.12.10",
        "inkcre.extension-api": "2.1.0",
    }

    assert target_matches(later, compatible_profile)
    assert select_compatible_target([later, earlier], compatible_profile) == earlier
    assert not target_matches(later, compatible_profile | {"python": "3.13.0"})
    assert not target_matches(later, {"inkcre.integration": "python-bundle-v1"})


class _Hooks:
    def __init__(self, events: list[str], *, fail_activate: bool = False) -> None:
        self.events = events
        self.fail_activate = fail_activate

    def initialize(self) -> None:
        self.events.append("initialize")

    def activate(self) -> None:
        self.events.append("activate")
        if self.fail_activate:
            raise RuntimeError("activation failed")

    def deactivate(self) -> None:
        self.events.append("deactivate")

    def dispose(self) -> None:
        self.events.append("dispose")


@pytest.mark.asyncio
async def test_python_lifecycle_enables_disables_and_compensates_partial_activation() -> None:
    success_events: list[str] = []
    lifecycle = ExtensionLifecycle(lambda: _Hooks(success_events))

    await lifecycle.enable()
    assert lifecycle.state == ExtensionState.ACTIVE
    await lifecycle.disable()
    assert lifecycle.state == ExtensionState.UNLOADED
    assert success_events == ["initialize", "activate", "deactivate", "dispose"]

    failure_events: list[str] = []
    failing = ExtensionLifecycle(lambda: _Hooks(failure_events, fail_activate=True))
    with pytest.raises(RuntimeError, match="activation failed"):
        await failing.enable()
    assert failing.state == ExtensionState.ERROR
    assert failure_events == ["initialize", "activate", "deactivate", "dispose"]


def test_python_consumer_rejects_nonpublished_release_and_unsafe_file_path() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "namespace": "inkcre",
                "name": "twitter",
                "version": "0.1.0",
                "state": "yanked",
                "targets": [],
            },
        )

    with RegistryClient(
        "https://registry.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(RegistryReleaseStateError, match="not installable"):
            client.get_release("inkcre", "twitter", "0.1.0")
        with pytest.raises(ValueError, match="traversal-free"):
            client.artifact_file_url(f"sha256:{'a' * 64}", "../secret")
