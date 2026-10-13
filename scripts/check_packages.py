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


def check_production_delivery_boundary() -> None:
    from contextlib import redirect_stdout

    import httpx
    import registry_production

    client_type = httpx.Client
    for status, stack, expected_error in [
        (200, "container", None),
        (401, "container", httpx.HTTPStatusError),
        (200, "cedar", ValueError),
    ]:
        events = []
        raw_output = io.BytesIO()
        output = io.TextIOWrapper(raw_output, encoding="utf-8")

        def provider(request, events=events, status=status, stack=stack, raw=raw_output):
            # A redirected, buffered stdout must expose the phase before provider I/O.
            assert b"phase=app_access status=started" in raw.getvalue()
            assert request.headers["Authorization"] == "Bearer synthetic-token"
            events.append((request.method, request.url.path))
            return httpx.Response(status, json={"stack": {"name": stack}})

        def client_factory(*args, provider=provider, **kwargs):
            return client_type(*args, transport=httpx.MockTransport(provider), **kwargs)

        with (
            patch.dict(
                os.environ,
                {
                    "HEROKU_API_KEY": "synthetic-token",
                    "HEROKU_APP_NAME": "owned-fixture",
                    "SOURCE_SHA": "exact-sha",
                },
                clear=True,
            ),
            patch.object(sys, "argv", ["registry_production.py", "--verify"]),
            patch.object(registry_production.httpx, "Client", client_factory),
            patch.object(
                registry_production, "run", side_effect=AssertionError("command in verify")
            ),
            patch.object(
                registry_production,
                "configure_runtime_login",
                side_effect=AssertionError("database mutation in verify"),
            ),
            patch.object(
                registry_production, "smoke", side_effect=AssertionError("smoke in verify")
            ),
            redirect_stdout(output),
        ):
            try:
                registry_production.main()
            except Exception as error:
                assert expected_error is not None and isinstance(error, expected_error)
            else:
                assert expected_error is None
        assert events == [("GET", "/apps/owned-fixture")]
        visible = raw_output.getvalue().decode()
        assert f"status={'failed' if expected_error else 'success'}" in visible
        assert "synthetic-token" not in visible
        output.close()

    environment = {
        "MIGRATION_DATABASE_URL": "postgres://owner:synthetic@localhost/registry",
        "DATABASE_URL": "postgres://registry_app:synthetic@localhost/registry",
        "HEROKU_API_KEY": "synthetic-token",
        "S3_ENDPOINT_URL": "https://objects.invalid",
        "S3_BUCKET": "synthetic-bucket",
        "DOCUMENTATION_ORIGIN_TEMPLATE": "https://docs-{snapshot}.invalid",
        "AWS_ACCESS_KEY_ID": "synthetic-key",
        "AWS_SECRET_ACCESS_KEY": "synthetic-secret",
    }
    for quantity, state, partial, failure in [
        (1, None, False, None),
        (0, "up", False, None),
        (0, "starting", False, None),
        (0, "idle", False, None),
        (0, "unknown", False, None),
        (0, None, True, None),
        (0, None, False, "migration"),
        (0, None, False, "release"),
        (0, None, False, "smoke"),
        (0, "down", False, None),
        (0, "crashed", False, None),
    ]:
        events = []
        output = io.StringIO()

        def provider(
            request: httpx.Request, events=events, quantity=quantity, state=state, partial=partial
        ) -> httpx.Response:
            events.append((request.method, request.url.path))
            if request.url.path.endswith("/formation/web"):
                body = {"type": "web", "quantity": quantity}
            elif request.url.path.endswith("/dynos"):
                body = [] if state is None else [{"type": "web", "state": state}]
                return httpx.Response(206 if partial else 200, json=body)
            else:
                body = {"stack": {"name": "container"}}
            return httpx.Response(200, json=body)

        def command(*args, events=events, failure=failure, **kwargs):
            events.append(tuple(args))
            if (failure == "migration" and args[:2] == ("docker", "run")) or (
                failure == "release" and args[:2] == ("heroku", "container:release")
            ):
                raise RuntimeError("synthetic command failure")
            return ""

        def login(*args, events=events):
            events.append(("database-login",))

        def smoke(*args, events=events, failure=failure):
            events.append(("smoke", *args))
            if failure == "smoke":
                raise RuntimeError("synthetic smoke failure")

        refused = quantity != 0 or state in {"up", "starting", "idle", "unknown"} or partial
        with (
            httpx.Client(
                base_url="https://api.heroku.com/", transport=httpx.MockTransport(provider)
            ) as client,
            patch.dict(os.environ, environment),
            patch.object(registry_production, "run", command),
            patch.object(registry_production, "configure_runtime_login", login),
            patch.object(registry_production, "smoke", smoke),
            redirect_stdout(output),
        ):
            try:
                registry_production.deploy(client, "owned-fixture", "verified-image", "exact-sha")
            except RuntimeError:
                assert refused or failure
            else:
                assert not refused and not failure
        if refused:
            assert all(event[0] == "GET" for event in events), events
            assert "phase=stopped_web_check status=failed" in output.getvalue()
        if failure in {"migration", "release"}:
            assert not any(event[:2] == ("heroku", "ps:scale") for event in events)
            assert f"phase={failure} status=failed" in output.getvalue()
        if not refused and failure not in {"migration", "release"}:
            scale = ("heroku", "ps:scale", "web=1:eco", "--app", "owned-fixture")
            release = ("heroku", "container:release", "web", "--app", "owned-fixture")
            assert events.count(scale) == 1 and events.index(release) < events.index(scale)
            assert (
                "docker",
                "tag",
                "verified-image",
                "registry.heroku.com/owned-fixture/web",
            ) in events
            assert ("smoke", "https://registry.inkcre.dev", "exact-sha") in events
        if failure == "migration":
            assert not any(event[0] in {"PATCH", "database-login"} for event in events)
        if failure == "smoke":
            assert "phase=smoke status=failed" in output.getvalue()
        assert "synthetic-secret" not in output.getvalue()
    print("Production stopped-web gate and ordered failure boundaries passed.")


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
    check_production_delivery_boundary()
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
