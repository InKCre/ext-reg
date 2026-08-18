from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from inkcre_extension_toolkit.preview import PreviewInventory

from inkcre_extension_registry.contracts.models import (
    ExtensionRecord,
    PrepareReleaseRequest,
    ReleaseRecord,
)
from inkcre_extension_registry.service.app import create_app

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def generated_contracts() -> dict[Path, bytes]:
    models = {
        "extension.schema.json": ExtensionRecord.model_json_schema(mode="serialization"),
        "prepare-release.schema.json": PrepareReleaseRequest.model_json_schema(
            mode="serialization"
        ),
        "release.schema.json": ReleaseRecord.model_json_schema(mode="serialization"),
        "preview-inventory.schema.json": PreviewInventory.model_json_schema(mode="validation"),
    }
    outputs = {CONTRACTS / name: _encoded(schema) for name, schema in models.items()}
    outputs[CONTRACTS / "openapi.json"] = _encoded(create_app().openapi())
    outputs[CONTRACTS / "revision.json"] = _encoded(
        {
            "contract_revision": 2,
            "distribution_kinds": ["module_federation", "python"],
            "extension_version": "strict-semver-without-build-metadata",
            "python_upload_filetypes": ["bdist_wheel"],
            "release_states": ["preparing", "published", "yanked", "blocked"],
            "simple_api_version": "1.1",
            "upload_limit_bytes": 20 * 1024 * 1024,
        }
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    outputs = generated_contracts()

    if arguments.check:
        stale = [
            path
            for path, expected in outputs.items()
            if not path.exists() or path.read_bytes() != expected
        ]
        if stale:
            parser.error("generated contracts are stale: " + ", ".join(str(path) for path in stale))
        return

    CONTRACTS.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
