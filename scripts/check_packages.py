"""Check Runtime native boundaries and install built Registry/Toolkit wheels in isolation."""

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
from types import SimpleNamespace
from unittest.mock import Mock, patch

from inkcre_extension_toolkit.preview import build_preview_registry
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def check_native_runtime_boundary() -> None:
    import asyncio

    from inkcre_extension_runtime_core_py import ExtensionEnvironmentApplicationRequiredError
    from inkcre_extension_runtime_core_py.distribution import (
        AcquiredDistribution,
        PipDistributionConsumer,
    )
    from inkcre_extension_runtime_core_py.errors import ExtensionRegistryError
    from inkcre_extension_runtime_core_py.manager import ExtensionManager
    from inkcre_extension_runtime_core_py.release import RegistryReleaseClient

    body = {
        "name": "check/extension",
        "nickname": "Check",
        "version": "1.2.3",
        "state": "published",
        "distribution": "python",
        "module_federation": None,
        "python": {
            "project": "check-extension",
            "host_sdk": "core-py",
            "host_sdk_version": ">=0.1.0",
            "simple_url": "/simple/check-extension/",
            "entry_point": {
                "group": "inkcre.core.extensions",
                "name": "extension",
                "object": "extensions.check:Extension",
            },
        },
    }
    response = Mock()
    response.json.return_value = body
    with patch("requests.get", return_value=response) as get:
        release = RegistryReleaseClient("https://registry.invalid").get("check/extension", "1.2.3")
        assert release.version == "1.2.3"
        assert get.call_args.args[0].endswith(
            "/v2/extensions/check/extension/distributions/python/releases/1.2.3"
        )
        assert release.python is not None
        commands: list[list[str]] = []
        installed_record = {
            "schema_version": 1,
            "name": release.name,
            "version": release.version,
            "host_sdk": {"name": "core-py", "version": ">=0.1.0"},
            "python": {
                "project": release.python.project,
                "project_version": "1.2.3",
                "entry_point": release.python.entry_point.model_dump(mode="json"),
            },
        }

        def runner(arguments: list[str]) -> subprocess.CompletedProcess[str]:
            commands.append(arguments)
            if arguments[0] == "download":
                destination = Path(arguments[arguments.index("--dest") + 1])
                with zipfile.ZipFile(
                    destination / "check_extension-1.2.3-py3-none-any.whl", "w"
                ) as wheel:
                    wheel.writestr(
                        "check_extension-1.2.3.dist-info/inkcre-extension.json",
                        json.dumps(installed_record),
                    )
            return subprocess.CompletedProcess(arguments, 0, "", "")

        consumer = PipDistributionConsumer("https://registry.invalid", runner=runner)
        with tempfile.TemporaryDirectory(prefix="runtime-wheel-check-") as directory:
            wheel_path = consumer.download(release, release.python, "0.1.0", Path(directory))
            assert [command[0] for command in commands] == ["download"]
            acquired = Mock()
            with patch.object(AcquiredDistribution, "discover", return_value=acquired):
                assert consumer.apply(wheel_path, release, release.python, "0.1.0") is acquired
            assert [command[0] for command in commands] == ["download", "install"]
        body["distribution"] = "module_federation"
        try:
            RegistryReleaseClient("https://registry.invalid").get("check/extension", "1.2.3")
        except ExtensionRegistryError:
            pass
        else:
            raise AssertionError("Python reader accepted a different native coordinate")

    store = Mock()
    store.get_participation.return_value = SimpleNamespace(
        name="check/extension", distribution="python", version="1.2.3", enabled=False
    )
    manager = ExtensionManager(
        store,
        Mock(),
        peer_id="peer-check",
        registry_origin="https://registry.invalid",
        host_version="0.1.0",
    )
    with (
        patch.object(AcquiredDistribution, "discover", return_value=None),
        patch(
            "subprocess.run",
            side_effect=AssertionError("running Peer attempted environment mutation"),
        ),
    ):
        try:
            asyncio.run(manager.enable("check/extension"))
        except ExtensionEnvironmentApplicationRequiredError:
            pass
        else:
            raise AssertionError("missing wheel must require stopped-Peer environment application")
    store.set_participation_enabled.assert_not_called()


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
        assert json.loads((output / "v2/extensions.json").read_text()) == [
            {"name": "check/catalog", "nickname": "Catalog check"}
        ]
        detail = json.loads(
            (
                output / "v2/extensions/check/catalog/distributions/module_federation.json"
            ).read_text()
        )
        assert detail["name"] == "check/catalog" and detail["releases"][0]["version"] == "1.10.0"
        redirects = (output / "_redirects").read_text()
        assert "/v2/extensions /v2/extensions.json 200" in redirects
        assert (
            "/v2/extensions/check/catalog/distributions/module_federation "
            "/v2/extensions/check/catalog/distributions/module_federation.json 200" in redirects
        )


def main() -> None:
    check_native_runtime_boundary()
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
