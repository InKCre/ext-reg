from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from inkcre_extension_toolkit.preview import PreviewInventory

from inkcre_extension_registry.contracts.models import (
    ExtensionRecord,
    InstalledExtension,
    PrepareReleaseRequest,
    PythonConsumerContracts,
    ReleaseRecord,
)
from inkcre_extension_registry.service.app import create_app

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
TOOLKIT_GENERATED = ROOT / "toolkit/src/inkcre_extension_toolkit/generated"


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def generated_contracts() -> dict[Path, bytes]:
    models = {
        "extension.schema.json": ExtensionRecord.model_json_schema(mode="serialization"),
        "prepare-release.schema.json": PrepareReleaseRequest.model_json_schema(
            mode="serialization"
        ),
        "release.schema.json": ReleaseRecord.model_json_schema(mode="serialization"),
        "python-installed-extension.schema.json": InstalledExtension.model_json_schema(
            mode="serialization"
        ),
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


def _generate_python_binding(schema: bytes, output: Path) -> bytes:
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        schema_path = temporary / "schema.json"
        generated_path = temporary / output.name
        schema_path.write_bytes(schema)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(schema_path),
                "--input-file-type",
                "jsonschema",
                "--output",
                str(generated_path),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.12",
                "--use-standard-collections",
                "--use-union-operator",
                "--use-annotated",
                "--field-constraints",
                "--strict-nullable",
                "--enum-field-as-literal",
                "all",
                "--enable-faux-immutability",
                "--disable-timestamp",
            ],
            check=True,
        )
        subprocess.run(["ruff", "format", str(generated_path)], check=True)
        return generated_path.read_bytes()


def generated_python_bindings() -> dict[Path, bytes]:
    return {
        TOOLKIT_GENERATED / "contracts.py": _generate_python_binding(
            _encoded(PythonConsumerContracts.model_json_schema(mode="serialization")),
            TOOLKIT_GENERATED / "contracts.py",
        ),
        TOOLKIT_GENERATED / "installed_extension.py": _generate_python_binding(
            _encoded(InstalledExtension.model_json_schema(mode="serialization")),
            TOOLKIT_GENERATED / "installed_extension.py",
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    outputs = generated_contracts() | generated_python_bindings()

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
    TOOLKIT_GENERATED.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
