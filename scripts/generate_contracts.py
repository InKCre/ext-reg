from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from inkcre_extension_registry.contracts.models import (
    KNOWN_CONDITION_KEYS,
    ExtensionRecord,
    ReleaseRecord,
    TargetAssociation,
    TargetManifest,
    TargetPublishConfig,
)
from inkcre_extension_registry.service.app import create_app

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _openapi() -> dict[str, Any]:
    document = create_app().openapi()
    document["paths"]["/v1/artifacts/{target_digest}/files/{relative_path}"] = {
        "get": {
            "operationId": "get_artifact_file",
            "parameters": [
                {
                    "in": "path",
                    "name": "target_digest",
                    "required": True,
                    "schema": {
                        "pattern": "^sha256:[0-9a-f]{64}$",
                        "type": "string",
                    },
                },
                {
                    "description": "Normalized POSIX path, including nested segments.",
                    "in": "path",
                    "name": "relative_path",
                    "required": True,
                    "schema": {"minLength": 1, "type": "string"},
                },
            ],
            "responses": {
                "200": {
                    "content": {"application/octet-stream": {"schema": {"type": "string"}}},
                    "description": "Immutable target file bytes.",
                },
                "404": {"description": "Target or file not found."},
                "451": {"description": "The associated release is operator-blocked."},
            },
            "summary": "Read one digest-addressed target file",
            "tags": ["artifacts"],
        }
    }
    return document


def generated_contracts() -> dict[Path, bytes]:
    models = {
        "extension.schema.json": ExtensionRecord.model_json_schema(mode="serialization"),
        "release.schema.json": ReleaseRecord.model_json_schema(mode="serialization"),
        "target-association.schema.json": TargetAssociation.model_json_schema(mode="serialization"),
        "target-manifest.schema.json": TargetManifest.model_json_schema(mode="serialization"),
        "target-publish-config.schema.json": TargetPublishConfig.model_json_schema(
            mode="serialization"
        ),
    }
    outputs = {CONTRACTS / name: _encoded(schema) for name, schema in models.items()}
    outputs[CONTRACTS / "openapi.json"] = _encoded(_openapi())
    outputs[CONTRACTS / "revision.json"] = _encoded(
        {
            "artifact_formats": ["module-federation-esm-v1", "python-bundle-v1"],
            "condition_keys": sorted(KNOWN_CONDITION_KEYS),
            "contract_revision": 1,
            "extension_version": "strict-semver-without-build-metadata",
            "release_states": ["preparing", "published", "yanked", "blocked"],
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
