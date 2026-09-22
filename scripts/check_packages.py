"""Install the built Registry and Toolkit wheels without workspace/editable imports."""

from __future__ import annotations

import email
import json
import os
import subprocess
import tempfile
import tomllib
import venv
import zipfile
from pathlib import Path

from inkcre_extension_toolkit.preview import build_preview_registry
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def check_preview_catalog() -> None:
    with tempfile.TemporaryDirectory(prefix="registry-preview-check-") as temporary:
        root = Path(temporary)
        artifact = root / "remote"
        artifact.mkdir()
        (artifact / "mf-manifest.json").write_text(
            json.dumps(
                {
                    "metaData": {
                        "publicPath": "./",
                        "remoteEntry": {"name": "remoteEntry.js", "path": ""},
                    }
                }
            )
        )
        (artifact / "remoteEntry.js").write_text("export const check = true;")
        producer = root / "package.json"
        producer.write_text(
            json.dumps(
                {
                    "version": "1.10.0",
                    "inkcre": {
                        "name": "check/catalog",
                        "nickname": "Catalog check",
                        "module_federation": {
                            "host_sdk": "@inkcre/core",
                            "host_sdk_version": ">=0.3.0 <0.4.0",
                        },
                    },
                }
            )
        )
        inventory = root / "inventory.json"
        inventory.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "distributions": [
                        {
                            "kind": "module_federation",
                            "producer": producer.name,
                            "artifact": artifact.name,
                        }
                    ],
                }
            )
        )
        output = root / "output"
        build_preview_registry(inventory, "https://registry.example.test", output)
        assert json.loads((output / "v1/extensions.json").read_text()) == [
            {"name": "check/catalog", "nickname": "Catalog check"}
        ]
        detail = json.loads((output / "v1/extensions/check/catalog.json").read_text())
        assert detail["name"] == "check/catalog" and detail["releases"][0]["version"] == "1.10.0"
        redirects = (output / "_redirects").read_text()
        assert "/v1/extensions /v1/extensions.json 200" in redirects
        assert "/v1/extensions/check/catalog /v1/extensions/check/catalog.json 200" in redirects


def main() -> None:
    check_preview_catalog()
    wheels = []
    for directory in (ROOT, ROOT / "toolkit"):
        project = tomllib.loads((directory / "pyproject.toml").read_text())["project"]
        wheels.append(
            ROOT
            / "dist"
            / f"{project['name'].replace('-', '_')}-{project['version']}-py3-none-any.whl"
        )
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_path = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = email.message_from_bytes(archive.read(metadata_path))
    requirement = next(
        item
        for value in metadata.get_all("Requires-Dist", [])
        if (item := Requirement(value)).name == "inkcre-extension-toolkit"
    )
    # 0.2.1 lacks documentation admission, even if the workspace import succeeds.
    assert "0.2.1" not in requirement.specifier, (
        "Registry wheel admits Toolkit without documentation API"
    )
    with tempfile.TemporaryDirectory(prefix="registry-wheel-check-") as temporary:
        environment = Path(temporary)
        venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                *map(str, wheels),
            ],
            cwd=environment,
            check=True,
        )
        subprocess.run([str(python), "-I", "-m", "pip", "check"], cwd=environment, check=True)
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from inkcre_extension_registry.service.app import create_app; "
                "from inkcre_extension_toolkit.documentation import inspect_documentation; "
                "assert create_app().openapi()['paths']['/v1/documentation-hosting']",
            ],
            cwd=environment,
            check=True,
        )
    print("Registry and Toolkit wheel metadata, isolated installation and service import passed.")


if __name__ == "__main__":
    main()
