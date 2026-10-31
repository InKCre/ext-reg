"""Exercise Registry migrations and HTTP behavior on a disposable PostgreSQL database.

REGISTRY_TEST_DATABASE_URL must identify an empty disposable database. S3 is a
local Moto server; no Cloudflare credentials or deployed resources are used.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import secrets
import zipfile
from unittest.mock import patch

import httpx
import psycopg
from check_d1_import import check_import
from check_documentation import check_documentation
from moto.server import ThreadedMotoServer
from registry_database import configure_runtime_login
from tortoise import Tortoise
from tortoise.backends.base.executor import EXECUTOR_CACHE
from tortoise.context import TortoiseContext
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.executor import MigrationExecutor, MigrationTarget
from tortoise.migrations.graph import MigrationKey

from inkcre_extension_registry.service import database as db
from inkcre_extension_registry.service.app import create_app
from inkcre_extension_registry.service.repository import RegistryRepository
from inkcre_extension_registry.service.settings import database_config


def archive(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    return output.getvalue()


async def journey(client: httpx.AsyncClient, token: str, other_token: str, artifacts) -> None:
    authorization = {"Authorization": f"Bearer {token}"}

    async def request(method: str, path: str, expected: int = 200, *, private=False, **kwargs):
        response = await client.request(
            method,
            path,
            headers={**(authorization if private else {}), **kwargs.pop("headers", {})},
            **kwargs,
        )
        assert response.status_code == expected, (
            f"{method} {path}: {response.status_code}: {response.text[:800]}"
        )
        return response

    root = "/v2/extensions/check/extension/distributions"
    python_path, mf_path = (
        root + "/python/releases/1.0.0",
        root + "/module_federation/releases/2.0.0",
    )
    provenance = {
        "source_repository": "https://example.invalid/check",
        "source_revision": "fixed-revision",
    }
    python = {
        **provenance,
        "project": "check-extension",
        "host_sdk": "core-py",
        "host_sdk_version": "^1.0.0",
        "entry_point": {
            "group": "inkcre.core.extensions",
            "name": "check",
            "object": "check:Extension",
        },
    }
    mf = {**provenance, "host_sdk": "@inkcre/core", "host_sdk_version": "^1.0.0"}
    py_prepare = {"nickname": "Check", "version": "1.0.0", "python": python}
    mf_prepare = {"nickname": "Check", "version": "2.0.0", "module_federation": mf}
    await request(
        "POST", "/v1/extensions/check/extension/releases", 410, private=True, json=py_prepare
    )
    await request("POST", root + "/python/releases", 401, json=py_prepare)
    await request(
        "POST",
        root.replace("check/", "other/") + "/python/releases",
        403,
        private=True,
        json=py_prepare,
    )
    await request("POST", root + "/python/releases", private=True, json=py_prepare)
    await request("POST", root + "/python/releases", private=True, json=py_prepare)
    await request(
        "POST",
        root + "/python/releases",
        409,
        private=True,
        json={**py_prepare, "python": {**python, "source_revision": "different"}},
    )
    await request("POST", root + "/python/releases", 409, private=True, json=mf_prepare)
    await request(
        "POST",
        root + "/python/releases",
        422,
        private=True,
        json={**py_prepare, "module_federation": mf},
    )
    await request("POST", root + "/module_federation/releases", private=True, json=mf_prepare)
    await request("GET", python_path, 404)
    await request("POST", python_path + "/publish", 409, private=True)
    await request("POST", mf_path + "/publish", 409, private=True)
    snapshot = archive(
        {
            "mf-manifest.json": json.dumps(
                {
                    "metaData": {
                        "publicPath": "./",
                        "remoteEntry": {"name": "remoteEntry.js", "path": ""},
                    }
                }
            ),
            "remoteEntry.js": "export const check = true;",
        }
    )
    await request(
        "POST",
        mf_path + "/module-federation",
        private=True,
        files={"content": ("extension.zip", snapshot)},
    )
    stored_mf = await db.ModuleFederationDistribution.get()
    remote_key = stored_mf.manifest_r2_key.removesuffix("mf-manifest.json") + "remoteEntry.js"
    # Corrupt immutable staging bytes must remain a domain conflict through the
    # concurrent storage boundary, and must not publish or change the association.
    await artifacts.put(remote_key, b"corrupt", content_type="text/javascript")
    await request(
        "POST",
        mf_path + "/module-federation",
        409,
        private=True,
        files={"content": ("extension.zip", snapshot)},
    )
    assert (await db.ModuleFederationDistribution.get()).internal_snapshot_hash == (
        stored_mf.internal_snapshot_hash
    )
    assert (await db.NativeRelease.get(distribution="module_federation")).state == "preparing"
    artifacts.client.delete_object(Bucket=artifacts.bucket, Key=remote_key)
    await request("POST", mf_path + "/publish", 409, private=True)
    await artifacts.put(remote_key, b"export const check = true;", content_type="text/javascript")
    mf_record = (await request("POST", mf_path + "/publish", private=True)).json()
    assert mf_record["distribution"] == "module_federation" and mf_record["python"] is None
    await request("GET", python_path, 404)
    metadata = "Metadata-Version: 2.3\nName: check-extension\nVersion: 1.0.0\n\n"
    wheel = archive(
        {
            "check.py": "class Extension: pass\n",
            "check_extension-1.0.0.dist-info/METADATA": metadata,
            "check_extension-1.0.0.dist-info/entry_points.txt": (
                "[inkcre.core.extensions]\ncheck = check:Extension\n"
            ),
            "check_extension-1.0.0.dist-info/WHEEL": (
                "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
            ),
            "check_extension-1.0.0.dist-info/RECORD": "",
        }
    )
    wheel_name = "check_extension-1.0.0-py3-none-any.whl"
    upload = {
        ":action": "file_upload",
        "protocol_version": "1",
        "name": "check-extension",
        "version": "1.0.0",
        "filetype": "bdist_wheel",
        "metadata_version": "2.3",
        "sha256_digest": hashlib.sha256(wheel).hexdigest(),
    }
    await request(
        "POST",
        "/legacy/",
        409,
        private=True,
        data={**upload, "sha256_digest": "0" * 64},
        files={"content": (wheel_name, wheel)},
    )
    for _ in range(2):
        await request(
            "POST", "/legacy/", private=True, data=upload, files={"content": (wheel_name, wheel)}
        )
    file = await db.PythonFile.get()
    artifacts.client.delete_object(Bucket=artifacts.bucket, Key=file.metadata_r2_key)
    await request("POST", python_path + "/publish", 409, private=True)
    await artifacts.put(
        file.metadata_r2_key, metadata.encode(), content_type="application/octet-stream"
    )
    original_check = RegistryRepository._release_objects_available

    async def concurrent_file_upload(repository, row):
        ready = await original_check(repository, row)
        fields = await db.PythonFile.filter(id=file.id).values()
        fields[0].pop("id")
        fields[0]["filename"] = "check_extension-1.0.0-1-py3-none-any.whl"
        fields[0]["r2_key"] += ".concurrent"
        fields[0]["metadata_r2_key"] += ".concurrent"
        await artifacts.put(fields[0]["r2_key"], wheel, content_type="application/octet-stream")
        await artifacts.put(
            fields[0]["metadata_r2_key"], metadata.encode(), content_type="application/octet-stream"
        )
        await db.PythonFile.create(**fields[0])
        return ready

    with patch.object(RegistryRepository, "_release_objects_available", concurrent_file_upload):
        await request("POST", python_path + "/publish", 409, private=True)
    assert (await db.NativeRelease.get(distribution="python")).state == "preparing"
    py_record = (await request("POST", python_path + "/publish", private=True)).json()
    assert py_record["distribution"] == "python" and py_record["module_federation"] is None
    await request("POST", python_path + "/publish", private=True)
    py_versions = (await request("GET", root + "/python")).json()["releases"]
    mf_versions = (await request("GET", root + "/module_federation")).json()["releases"]
    assert [r["version"] for r in py_versions] == ["1.0.0"] and [
        r["version"] for r in mf_versions
    ] == ["2.0.0"]
    await request("GET", "/explore/check/extension?distribution=python&version=1.0.0")
    await request("GET", "/explore/check/extension?distribution=module_federation&version=2.0.0")
    assert (await request("GET", "/v1/extensions")).json() == []
    await request("GET", "/v1/extensions/check/extension/releases/1.0.0", 404)
    package = f"/packages/check-extension/1.0.0/{wheel_name}"
    remote = "/extensions/check/extension/2.0.0/module-federation/remoteEntry.js"
    assert (await request("GET", package)).content == wheel
    assert (await request("GET", package + ".metadata")).text == metadata
    assert (await request("GET", remote)).content == b"export const check = true;"
    for path in (package, remote):
        fetched = await request("GET", path)
        await request("GET", path, 304, headers={"If-None-Match": fetched.headers["etag"]})
    await request(
        "POST", python_path + "/yank", private=True, json={"reason": "withdraw Python only"}
    )
    assert (await request("GET", mf_path)).json()["state"] == "published"
    await request("GET", package)
    await request("POST", python_path + "/unyank", private=True)
    legacy = await db.Release.create(
        extension_id="check/extension",
        version="1.0.0",
        state="published",
        visible_distributions=["python"],
    )
    py = await db.PythonDistribution.get()
    py.legacy_release = legacy
    await py.save(update_fields=["legacy_release_id"])
    historical = (await request("GET", "/v1/extensions/check/extension/releases/1.0.0")).json()
    assert (
        historical["python"]
        and historical["module_federation"] is None
        and "distribution" not in historical
    )
    await db.NativeRelease.filter(distribution="python").update(state="blocked")
    assert (await request("GET", "/v1/extensions")).json() == []
    await request("GET", python_path, 451)
    await request("GET", package, 451, headers={"If-None-Match": "*"})
    await request("GET", "/v1/extensions/check/extension/releases/1.0.0", 451)
    await request("GET", mf_path)
    await request("GET", remote)
    await db.NativeRelease.filter(distribution="python").update(state="published")
    await check_documentation(client, token, other_token, artifacts)
    await db.Credential.all().update(disabled=True)
    await request("GET", "/v2/publisher", 401, private=True)


def check_runtime_permissions(url: str) -> None:
    with psycopg.connect(url, autocommit=True) as connection:
        for statement in (
            "CREATE TABLE forbidden (id integer)",
            "ALTER TABLE namespaces ADD COLUMN forbidden integer",
            "DELETE FROM tortoise_migrations",
            "CREATE ROLE forbidden NOLOGIN",
        ):
            try:
                with connection.transaction():
                    connection.execute(statement)
                    raise AssertionError("Runtime login unexpectedly has migration authority")
            except psycopg.errors.InsufficientPrivilege:
                pass


async def check_native_upgrade(executor: MigrationExecutor) -> None:
    """Replay a populated pre-v2 schema through the admitted migration boundary."""
    from datetime import UTC, datetime

    from tortoise.migrations.schema_generator.state import State
    from tortoise.migrations.schema_generator.state_apps import StateApps

    target = MigrationKey("models", "0004_documentation_ownership")
    await executor.migrate([MigrationTarget(target.app_label, target.name)], direction="forward")
    state = State(models={}, apps=StateApps(default_connections={"models": "default"}))
    for key in executor.loader.graph.forwards_plan(target):
        await executor.loader.graph.nodes[key].apply(state, dry_run=True, schema_editor=None)
    old = {
        name: state.apps.get_model("models." + name)
        for name in (
            "Namespace",
            "Extension",
            "Release",
            "PythonDistribution",
            "ModuleFederationDistribution",
            "PythonFile",
            "DocumentationSnapshot",
            "DocumentationSet",
        )
    }
    namespace = await old["Namespace"].create(name="upgrade")
    extension = await old["Extension"].create(
        name="upgrade/mail", namespace=namespace, nickname="Upgrade"
    )
    legacy = await old["Release"].create(
        extension=extension, version="1.0.0", state="published", published_at=datetime.now(UTC)
    )
    python = await old["PythonDistribution"].create(
        release=legacy,
        normalized_project="upgrade-mail",
        project_version="1.0.0",
        host_sdk="core-py",
        host_sdk_range="^1.0.0",
        entry_group="inkcre.core.extensions",
        entry_name="upgrade",
        entry_object="upgrade:Extension",
        source_repository="https://example.invalid",
        source_revision="old-source",
    )
    await old["ModuleFederationDistribution"].create(
        release=legacy,
        host_sdk="@inkcre/core",
        host_sdk_range="^1.0.0",
        source_repository="https://example.invalid",
        source_revision="old-source",
    )
    await old["PythonFile"].create(
        distribution=python,
        filename="upgrade_mail-1.0.0-py3-none-any.whl",
        sha256="a" * 64,
        size=4,
        filetype="bdist_wheel",
        core_metadata_sha256="b" * 64,
        r2_key="preserved/wheel",
        metadata_r2_key="preserved/metadata",
    )
    snapshot = await old["DocumentationSnapshot"].create(
        id="c" * 32,
        release=legacy,
        scope="global",
        content_sha256="d" * 64,
        entry="index.html",
        source_repository="https://example.invalid",
        source_revision="old-source",
        files={"index.html": {"media_type": "text/html", "size": 4}},
        etag="e" * 64,
    )
    await old["DocumentationSet"].create(release=legacy, scope="global", snapshot=snapshot)
    files_before = await old["PythonFile"].all().values()
    docs_before = await old["DocumentationSnapshot"].all().values()
    await executor.migrate(direction="forward")
    # Historical and current model classes share table names; discard old SQL shapes.
    EXECUTOR_CACHE.clear()
    assert await db.PythonFile.all().values() == files_before
    native = await db.NativeRelease.get(
        extension_id=extension.name, distribution="python", version="1.0.0"
    )
    assert native.state == "published"
    mf = await db.NativeRelease.get(
        extension_id=extension.name, distribution="module_federation", version="1.0.0"
    )
    assert mf.state == "preparing", "unuploaded legacy MF must not become published"
    migrated = await db.Release.get(id=legacy.id)
    assert migrated.visible_distributions == ["python"]
    docs_after = await db.DocumentationSnapshot.all().values()
    for row in docs_after:
        assert row.pop("native_release_id") is None
    assert docs_after == docs_before, "historical snapshot identity, receipt and owner changed"
    pointer = await db.DocumentationSet.get(snapshot_id=snapshot.id)
    assert pointer.release_id == legacy.id and pointer.native_release_id is None
    for model in (
        db.DocumentationSet,
        db.DocumentationSnapshot,
        db.PythonFile,
        db.PythonDistribution,
        db.ModuleFederationDistribution,
        db.NativeRelease,
        db.Release,
        db.Extension,
        db.Namespace,
    ):
        await model.all().delete()
    print(
        "Populated pre-v2 migration preserved native bytes references "
        "and historical document receipts."
    )


async def main() -> None:
    owner_url = os.environ["REGISTRY_TEST_DATABASE_URL"]
    config = database_config(owner_url)
    async with TortoiseContext() as context:
        await context.init(config=config)
        assert Tortoise.apps is not None
        assert not await MigrationAutodetector(Tortoise.apps, config["apps"]).changes(), (
            "Models changed without a checked-in migration"
        )
        executor = MigrationExecutor(Tortoise.get_connection("default"), config["apps"])
        await executor.loader.build_graph()
        if not await executor.recorder.applied_migrations():
            await check_native_upgrade(executor)
        else:
            await executor.migrate(direction="forward")
        assert not await executor.plan(), "Migration head was not reached"
        assert not await db.Namespace.exists(), "Checks require an empty disposable database"
    url = await asyncio.to_thread(configure_runtime_login, owner_url, secrets.token_urlsafe(32))
    await asyncio.to_thread(check_runtime_permissions, url)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    os.environ.update(
        DATABASE_URL=url,
        PUBLIC_ORIGIN="http://localhost",
        DOCUMENTATION_ORIGIN_TEMPLATE="http://{snapshot}.docs.localhost",
        S3_ENDPOINT_URL=f"http://{host}:{port}",
        S3_BUCKET="registry-check",
        AWS_ACCESS_KEY_ID="testing",
        AWS_SECRET_ACCESS_KEY="testing",
    )
    app = create_app()
    try:
        async with app.router.lifespan_context(app):
            app.state.repository.artifacts.client.create_bucket(
                Bucket="registry-check", CreateBucketConfiguration={"LocationConstraint": "auto"}
            )
            token, other_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            try:
                for namespace, credential in (("check", token), ("other", other_token)):
                    await db.Namespace.create(name=namespace)
                    await db.Credential.create(
                        token_hash=hashlib.sha256(credential.encode()).hexdigest(),
                        namespace_id=namespace,
                        label="Disposable verification",
                    )
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://localhost", timeout=30
                ) as client:
                    await journey(client, token, other_token, app.state.repository.artifacts)
                for model in reversed(
                    (
                        db.Namespace,
                        db.Credential,
                        db.Extension,
                        db.Release,
                        db.NativeRelease,
                        db.ModuleFederationDistribution,
                        db.PythonDistribution,
                        db.PythonFile,
                        db.DocumentationSnapshot,
                        db.DocumentationSet,
                    )
                ):
                    await model.all().delete()
                await check_import()
                print("Registry PostgreSQL migrations, transactions, HTTP and S3 checks passed.")
            finally:
                for model in (
                    db.DocumentationSet,
                    db.DocumentationSnapshot,
                    db.PythonFile,
                    db.PythonDistribution,
                    db.ModuleFederationDistribution,
                    db.NativeRelease,
                    db.Release,
                    db.Extension,
                    db.Credential,
                    db.Namespace,
                ):
                    await model.all().delete()
    finally:
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())
