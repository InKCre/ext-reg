"""Check Runtime native boundaries and install built Registry/Toolkit wheels in isolation."""

from __future__ import annotations

import email
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
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


def check_native_toolkit_cli(python: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        site = fixture / "site"
        site.mkdir()
        (site / "index.html").write_text("<!doctype html><title>Native documentation</title>")
        output = fixture / "candidate"
        subprocess.run(
            [
                str(python),
                "-I",
                str(python.parent / "inkcre-ext"),
                "docs",
                "pack",
                "--site",
                str(site),
                "--output",
                str(output),
                "--name",
                "check/extension",
                "--version",
                "1.0.0",
                "--distribution",
                "python",
                "--scope",
                "global",
                "--source-repository",
                "https://example.invalid/check",
                "--source-revision",
                "exact",
            ],
            cwd=fixture,
            check=True,
        )
        candidate = json.loads((output / "candidate.json").read_text())
        assert candidate["distribution"] == "python" and candidate["scope"] == "global"
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from inkcre_extension_toolkit.client import RegistryClient; "
                "assert all(not hasattr(RegistryClient, method) for method in "
                "('prepare','upload_module_federation','publish','yank','unyank')); "
                "assert all(hasattr(RegistryClient, method) for method in "
                "('prepare_native','publish_native','get_native_release','get_release','get_documentation'))",
            ],
            cwd=fixture,
            check=True,
        )
    print(
        "Installed Toolkit CLI persists native documentation identity; retired writes are absent."
    )


def check_coordinated_version_preparation() -> None:
    """Exercise the real CLI on a disposable Git history, without editing this checkout."""
    from release import projects

    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        base = "HEAD"
        archive = subprocess.check_output(["git", "archive", base], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(fixture, filter="data")

        def git(*arguments):
            return subprocess.check_output(
                ["git", *arguments], cwd=fixture, stderr=subprocess.DEVNULL
            )

        git("init", "--quiet")
        git("config", "user.name", "Registry qualification")
        git("config", "user.email", "qualification@example.invalid")
        for project in projects():
            path = fixture / project.pyproject.relative_to(ROOT)
            version = ".".join(map(str, project.version))
            major, minor, patch = project.version
            previous = (
                (major, minor, patch - 1)
                if patch
                else (major, minor - 1, 0)
                if minor
                else (major - 1, 0, 0)
            )
            baseline_version = ".".join(map(str, previous))
            path.write_text(
                path.read_text().replace(
                    f'version = "{version}"', f'version = "{baseline_version}"', 1
                )
            )
            (fixture / project.changelog.relative_to(ROOT)).write_text("# Changelog\n\n## 0.0.0\n")
        git("add", ".")
        git("commit", "--quiet", "-m", "baseline")
        baseline = git("rev-parse", "HEAD").decode().strip()
        for project in projects():
            for path in (project.pyproject, project.changelog):
                shutil.copyfile(path, fixture / path.relative_to(ROOT))
            target = fixture / project.fragments.relative_to(ROOT)
            shutil.rmtree(target, ignore_errors=True)
            target.mkdir()
        shutil.copyfile(ROOT / "scripts/release.py", fixture / "scripts/release.py")
        (fixture / "src/qualification.py").write_text("# Observable behavior-path candidate.\n")
        git("add", ".")
        git("commit", "--quiet", "-m", "coordinated candidate")

        def check(*arguments):
            return subprocess.run(
                [sys.executable, "scripts/release.py", "check", "--base", baseline, *arguments],
                cwd=fixture,
                capture_output=True,
                text=True,
                check=False,
            )

        strict = check()
        assert strict.returncode and "release PR contains behavior changes" in strict.stderr
        flag = "--allow-feature-version-preparation"
        admitted = check(flag)
        assert admitted.returncode == 0, admitted.stderr
        assert "This does not authorize publication" in admitted.stdout
        residual = fixture / ".changes/+residual.fixed.md"
        residual.write_text("An unconsumed release intent.\n")
        rejected = check(flag)
        assert rejected.returncode and "unconsumed fragments" in rejected.stderr
        residual.unlink()
        changelog = fixture / "CHANGELOG.md"
        original = changelog.read_text()
        root_version = ".".join(map(str, projects()[0].version))
        changelog.write_text(original.replace(f"## {root_version}", "## 99.0.0", 1))
        rejected = check(flag)
        assert rejected.returncode and "prepared changelog must begin" in rejected.stderr
        changelog.write_text(original)
        project_file = fixture / "pyproject.toml"
        original = project_file.read_text()
        project_file.write_text(
            original.replace(f'version = "{root_version}"', 'version = "0.0.0"', 1)
        )
        rejected = check(flag)
        assert rejected.returncode and "prepared version must increase" in rejected.stderr
        root_project = projects()[0]
        major, minor, patch = root_project.version
        previous = (
            (major, minor, patch - 1)
            if patch
            else (major, minor - 1, 0)
            if minor
            else (major - 1, 0, 0)
        )
        unchanged = ".".join(map(str, previous))
        project_file.write_text(
            original.replace(f'version = "{root_version}"', f'version = "{unchanged}"', 1)
        )
        rejected = check(flag)
        assert (
            rejected.returncode and "version and changelog must change together" in rejected.stderr
        )
    print("Coordinated version CLI admission and strict residual boundaries passed.")


def main() -> None:
    check_coordinated_version_preparation()
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
        toolkit_wheel = next(path for path in wheels if "inkcre_extension_toolkit-" in path.name)
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                f"{toolkit_wheel}[cli]",
            ],
            cwd=environment,
            check=True,
        )
        check_native_toolkit_cli(python)
    print("Registry and Toolkit wheel metadata, isolated installation and service import passed.")


if __name__ == "__main__":
    main()
