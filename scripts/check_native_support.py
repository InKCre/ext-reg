"""Exercise producer intent and Python Host support-change boundaries."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from inkcre_extension_runtime_core_py import (
    ExtensionManager,
    ExtensionNativeSupportChangeError,
    ExtensionRegistryError,
    ExtensionReleaseUnavailableError,
    ExtensionStateConflictError,
    require_native_support_preserved,
)
from inkcre_extension_runtime_core_py.contracts import ExtensionReleaseDescriptor
from inkcre_extension_runtime_core_py.release import RegistryReleaseClient
from inkcre_extension_toolkit.contracts import PrepareReleaseRequest
from inkcre_extension_toolkit.release_intent import ReleaseIntent


def check_native_support() -> None:
    def reject(operation, expected, inspect=lambda error: None):
        try:
            operation()
        except expected as error:
            inspect(error)
        else:
            raise AssertionError(f"Expected {expected.__name__}")

    name = "check/support"

    def check(previous, target, **kwargs):
        return require_native_support_preserved(name, "1.0.0", "2.0.0", previous, target, **kwargs)

    check(["python"], ["python", "module_federation"])
    check(["python", "module_federation"], ["python", "module_federation"])
    failures = []
    reject(
        lambda: check(["python", "module_federation"], ["python"]),
        ExtensionNativeSupportChangeError,
        failures.append,
    )
    assert failures[0].removed_formats == ("module_federation",)
    assert failures[0].reason == "reduced" and failures[0].installed_version == "1.0.0"
    reject(lambda: check(None, ["python"]), ExtensionNativeSupportChangeError, failures.append)
    assert failures[1].reason == "unavailable"
    for previous in (["python", "module_federation"], None):
        check(previous, ["python"], expected_installed_version="1.0.0", allow_support_change=True)
    reject(lambda: check(None, ["python"], allow_support_change=True), ValueError)
    reject(
        lambda: check(
            None, ["python"], expected_installed_version="0.9.0", allow_support_change=True
        ),
        ExtensionStateConflictError,
    )

    payload = {
        "nickname": "Support check",
        "version": "2.0.0",
        "module_federation": {
            "host_sdk": "@inkcre/core",
            "host_sdk_version": "^1.0.0",
            "source_repository": "https://example.invalid/repo",
            "source_revision": "revision",
        },
    }
    intent = ReleaseIntent(version="2.0.0", required_native_formats=("python", "module_federation"))
    prepared = intent.prepare(PrepareReleaseRequest.model_validate(payload))
    assert set(prepared.model_dump()["required_native_formats"]) == {"python", "module_federation"}
    reject(
        lambda: intent.prepare(
            PrepareReleaseRequest.model_validate({**payload, "version": "1.0.0"})
        ),
        ValueError,
    )
    reject(
        lambda: intent.prepare(
            PrepareReleaseRequest.model_validate(
                {**payload, "required_native_formats": ["module_federation"]}
            )
        ),
        ValueError,
    )
    reject(
        lambda: PrepareReleaseRequest.model_validate(
            {**payload, "required_native_formats": ["python", "python"]}
        ),
        ValueError,
    )

    reader = RegistryReleaseClient("https://registry.example")
    for status in (404, 451, 503):
        response = requests.Response()
        response.status_code = status
        with patch("inkcre_extension_runtime_core_py.release.requests.get", return_value=response):
            reject(
                lambda: reader.get(name, "1.0.0"),
                ExtensionReleaseUnavailableError if status != 503 else ExtensionRegistryError,
            )

    python = {
        "project": "check-support",
        "simple_url": "/simple/check-support/",
        "host_sdk": "core-py",
        "host_sdk_version": "^1.0.0",
        "entry_point": {
            "group": "inkcre.core.extensions",
            "name": "support",
            "object": "support:Extension",
        },
    }
    mf = {
        "host_sdk": "@inkcre/core",
        "host_sdk_version": "^1.0.0",
        "manifest_url": "/extensions/check/support/1.0.0/module-federation/mf-manifest.json",
    }
    old = ExtensionReleaseDescriptor.model_validate(
        {
            "name": name,
            "nickname": "Support",
            "version": "1.0.0",
            "state": "published",
            "python": python,
            "module_federation": mf,
        }
    )
    target = ExtensionReleaseDescriptor.model_validate(
        {**old.model_dump(), "version": "2.0.0", "module_federation": None}
    )
    current = SimpleNamespace(name=name, version="1.0.0", enabled=[])
    host = Mock()
    host.get.return_value = current
    host.install.return_value = SimpleNamespace(name=name, version="2.0.0", enabled=[])
    with (
        patch("inkcre_extension_runtime_core_py.manager._host_model", return_value=host),
        patch("inkcre_extension_runtime_core_py.manager._host_version", return_value="1.0.0"),
        patch(
            "inkcre_extension_runtime_core_py.manager._registry_origin",
            return_value="https://registry.example",
        ),
        patch.object(RegistryReleaseClient, "get") as get_release,
    ):
        manager = ExtensionManager()
        get_release.side_effect = [target, old]
        reject(lambda: manager.install(name, "2.0.0"), ExtensionNativeSupportChangeError)
        host.install.assert_not_called()
        get_release.side_effect = [target, old]
        manager.install(
            name, "2.0.0", expected_installed_version="1.0.0", allow_support_change=True
        )
        host.install.assert_called_once_with(name, "2.0.0", "Support", expected_version="1.0.0")
        host.install.reset_mock()
        get_release.side_effect = [target, ExtensionRegistryError("temporary")]
        reject(
            lambda: manager.install(
                name, "2.0.0", expected_installed_version="1.0.0", allow_support_change=True
            ),
            ExtensionRegistryError,
        )
        host.install.assert_not_called()
        get_release.side_effect = [target, ExtensionReleaseUnavailableError(451)]
        manager.install(
            name, "2.0.0", expected_installed_version="1.0.0", allow_support_change=True
        )
        current.enabled = ["peer"]
        host.install.reset_mock()
        reject(lambda: manager.install(name, "2.0.0"), ExtensionStateConflictError)
        host.install.assert_not_called()
    print("Producer exact intent and Python Runtime support-change checks passed.")
