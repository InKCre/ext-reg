"""Native wire semantics, generated consumers and stable flat Python APIs; no database."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

from inkcre_extension_runtime_core_py.contracts import ExtensionReleaseDescriptor
from inkcre_extension_runtime_core_py.errors import ExtensionRegistryError
from inkcre_extension_runtime_core_py.generated.registry import (
    NativeReleaseRecord as RuntimeNativeReleaseRecord,
)
from inkcre_extension_runtime_core_py.release import RegistryReleaseClient
from inkcre_extension_toolkit import contracts as toolkit
from inkcre_extension_toolkit.generated import contracts as generated
from pydantic import ValidationError

from inkcre_extension_registry.contracts import models as canonical

VECTORS = Path(__file__).parent / "fixtures/native-contracts.json"


def main() -> None:
    vectors = json.loads(VECTORS.read_text())
    validators = {
        "release": (
            canonical.NativeReleaseRecord.model_validate,
            generated.NativeReleaseRecord.model_validate,
            toolkit.NativeReleaseRecord.model_validate,
            ExtensionReleaseDescriptor.model_validate,
            RuntimeNativeReleaseRecord.model_validate,
        ),
        "prepare": (
            canonical.NativePrepareReleaseRequest.model_validate,
            generated.NativePrepareReleaseRequest.model_validate,
            toolkit.NativePrepareReleaseRequest.model_validate,
        ),
    }
    for kind, cases in vectors.items():
        for case in cases:
            for validate in validators[kind]:
                try:
                    validate(case["payload"])
                    accepted = True
                except ValidationError:
                    accepted = False
                assert accepted == case["valid"], (kind, case["id"], validate)

    # Public Python callers still construct flat objects and access attributes, not .root.
    for model in (
        canonical.NativeReleaseRecord,
        toolkit.NativeReleaseRecord,
        ExtensionReleaseDescriptor,
    ):
        value = model(**vectors["release"][0]["payload"])
        assert value.name == "inkcre/example" and value.python is not None
        assert value.module_federation is None
        assert value.model_dump(mode="json")["distribution"] == "python"
    nested = toolkit.NativeExtensionRecord(
        name="inkcre/example", nickname="Example", releases=[vectors["release"][0]["payload"]]
    )
    assert nested.releases[0].python is not None
    assert (
        canonical.NativePublisherRelease(
            **vectors["release"][0]["payload"], uploaded=True
        ).model_dump()["uploaded"]
        is True
    )

    # The actual public reader must reject malformed association and wrong exact coordinates.
    client = RegistryReleaseClient("https://registry.example.test")
    for case in vectors["release"]:
        response = Mock()
        response.json.return_value = case["payload"]
        with patch("inkcre_extension_runtime_core_py.release.requests.get", return_value=response):
            try:
                client.get("inkcre/example", "1.0.0")
                accepted = True
            except ExtensionRegistryError:
                accepted = False
        assert accepted == (case["valid"] and case["payload"]["distribution"] == "python"), case[
            "id"
        ]
    response = Mock()
    response.json.return_value = {**vectors["release"][0]["payload"], "version": "2.0.0"}
    with patch("inkcre_extension_runtime_core_py.release.requests.get", return_value=response):
        try:
            client.get("inkcre/example", "1.0.0")
        except ExtensionRegistryError:
            pass
        else:
            raise AssertionError("a different exact release was accepted")
    print("Native contract vectors and flat Python consumer APIs passed.")


if __name__ == "__main__":
    main()
