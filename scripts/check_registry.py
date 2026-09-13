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

import httpx
from check_d1_import import check_import
from moto.server import ThreadedMotoServer
from tortoise import Tortoise
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.executor import MigrationExecutor

from inkcre_extension_registry.service import database as db
from inkcre_extension_registry.service.app import create_app
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
            method, path, headers=authorization if private else {}, **kwargs
        )
        assert response.status_code == expected, (
            f"{method} {path}: expected {expected}, got {response.status_code}: "
            f"{response.text[:800]}"
        )
        return response

    release_path = "/v1/extensions/check/extension/releases"
    version_path = release_path + "/1.0.0"
    source = {"source_repository": "https://example.invalid/check", "source_revision": "rev' ? --"}
    association = {
        "nickname": "Publisher's extension",
        "version": "1.0.0",
        "python": {
            **source,
            "project": "check-extension",
            "host_sdk": "core-py",
            "host_sdk_version": "^1.0.0",
            "entry_point": {
                "group": "inkcre.core.extensions",
                "name": "check",
                "object": "check:Extension",
            },
        },
        "module_federation": {**source, "host_sdk": "@inkcre/core", "host_sdk_version": "^1.0.0"},
    }
    assert (await request("GET", "/v1/extensions")).json() == []
    await request("GET", "/")
    await request("GET", "/v1/publisher", 401)
    await request(
        "POST", "/v1/extensions/other/extension/releases", 403, private=True, json=association
    )
    await request("POST", release_path, private=True, json=association)
    await request("POST", release_path, private=True, json=association)
    await request(
        "POST", release_path, 409, private=True, json={**association, "nickname": "Changed"}
    )
    await request("GET", version_path, 404)
    await request("POST", version_path + "/publish", 409, private=True)
    workspace = (await request("GET", "/v1/publisher", private=True)).json()
    assert len(workspace["releases"]) == 1
    assert not workspace["releases"][0]["python_uploaded"]
    assert not workspace["releases"][0]["web_uploaded"]
    row = await db.PythonDistribution.get()
    assert row.source_revision == source["source_revision"] and row.build_id is None

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
    for _ in range(2):
        await request(
            "POST",
            "/legacy/",
            private=True,
            data={
                ":action": "file_upload",
                "protocol_version": "1",
                "name": "check-extension",
                "version": "1.0.0",
                "filetype": "bdist_wheel",
                "metadata_version": "2.3",
                "sha256_digest": hashlib.sha256(wheel).hexdigest(),
            },
            files={"content": (wheel_name, wheel)},
        )
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
    for _ in range(2):
        await request(
            "POST",
            version_path + "/module-federation",
            private=True,
            files={"content": ("extension.zip", snapshot)},
        )
    uploaded = (await request("GET", "/v1/publisher", private=True)).json()["releases"][0]
    assert uploaded["python_uploaded"] and uploaded["web_uploaded"]
    file = await db.PythonFile.get()
    artifacts.client.delete_object(Bucket=artifacts.bucket, Key=file.metadata_r2_key)
    await request("POST", version_path + "/publish", 409, private=True)
    await artifacts.put(
        file.metadata_r2_key, metadata.encode(), content_type="application/octet-stream"
    )
    await request("POST", version_path + "/publish", private=True)
    await request("POST", version_path + "/publish", private=True)
    assert (await request("GET", "/v1/extensions")).json()[0]["name"] == "check/extension"
    await request("GET", "/explore/check/extension?version=1.0.0")
    await request("GET", "/v1/extensions/check/extension")
    assert (await request("GET", version_path)).json()["state"] == "published"
    await request("GET", "/simple/")
    await request("GET", "/simple/check-extension/")
    package_path = f"/packages/check-extension/1.0.0/{wheel_name}"
    web_path = "/extensions/check/extension/1.0.0/module-federation/remoteEntry.js"
    assert (await request("GET", package_path)).content == wheel
    assert (await request("GET", package_path + ".metadata")).text == metadata
    await request("GET", web_path)
    head = await request("HEAD", package_path)
    assert head.content == b"" and head.headers["content-length"] == str(len(wheel))
    assert head.headers["etag"] == f'"{hashlib.sha256(wheel).hexdigest()}"'
    await request("HEAD", web_path)
    await request("GET", package_path.replace("check-extension", "CHECK_extension"), 404)
    await request("GET", web_path.replace("remoteEntry.js", "mf-manifest.json"))

    reason = "Publisher's withdrawal ?"
    await request("POST", version_path + "/yank", private=True, json={"reason": reason})
    assert (await request("GET", version_path)).json()["state"] == "yanked"
    assert (await request("GET", "/v1/extensions")).json() == []
    await request("GET", package_path)
    simple = await client.get(
        "/simple/check-extension/", headers={"Accept": "application/vnd.pypi.simple.v1+json"}
    )
    assert simple.json()["files"][0]["yanked"] == reason
    await request("POST", version_path + "/unyank", private=True)
    assert (await request("GET", version_path)).json()["state"] == "published"
    row = await db.Release.get()
    assert row.yank_reason is None and row.published_at and row.updated_at

    # Exercise correlated readiness expressions and the private pagination boundary.
    for minor in range(1, 11):
        await request(
            "POST",
            release_path,
            private=True,
            json={
                "nickname": association["nickname"],
                "version": f"1.{minor}.0",
                "module_federation": association["module_federation"],
            },
        )
    first = (await request("GET", "/v1/publisher", private=True)).json()
    last = (await request("GET", "/v1/publisher?offset=10", private=True)).json()
    assert len(first["releases"]) == 10 and first["next_offset"] == 10
    assert len(last["releases"]) == 1 and last["next_offset"] is None
    entries = first["releases"] + last["releases"]
    assert len({entry["version"] for entry in entries}) == 11
    assert sum(entry["python_uploaded"] for entry in entries) == 1
    assert sum(entry["web_uploaded"] for entry in entries) == 1
    other = await client.get("/v1/publisher", headers={"Authorization": f"Bearer {other_token}"})
    assert other.status_code == 200 and other.json()["namespace"] == "other"
    assert other.json()["releases"] == []

    # The project/version uniqueness conflict occurs after creating both identities.
    await request(
        "POST",
        "/v1/extensions/check/atomic/releases",
        409,
        private=True,
        json=association,
    )
    assert not await db.Extension.filter(name="check/atomic").exists()
    assert not await db.Release.filter(extension_id="check/atomic").exists()

    # Concurrent conflicting associations must converge to one immutable release.
    async def competing(revision: str):
        payload = {
            **association,
            "version": "3.0.0",
            "python": {
                **association["python"],
                "source_revision": revision,
            },
        }
        return await client.post(release_path, json=payload, headers=authorization)

    replies = await asyncio.gather(competing("first"), competing("second"))
    assert sorted(reply.status_code for reply in replies) == [200, 409]
    assert await db.Release.filter(version="3.0.0").count() == 1

    await db.Release.filter(version="1.0.0").update(state="blocked")
    await request("GET", version_path, 451)
    await request("GET", package_path, 451)
    await request("GET", web_path, 451)
    assert "check-extension" not in (await request("GET", "/simple/")).text
    await db.Credential.all().update(disabled=True)
    await request("GET", "/v1/publisher", 401, private=True)


async def main() -> None:
    url = os.environ["REGISTRY_TEST_DATABASE_URL"]
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    os.environ.update(
        DATABASE_URL=url,
        PUBLIC_ORIGIN="http://localhost",
        S3_ENDPOINT_URL=f"http://{host}:{port}",
        S3_BUCKET="registry-check",
        AWS_ACCESS_KEY_ID="testing",
        AWS_SECRET_ACCESS_KEY="testing",
    )
    app = create_app()
    try:
        async with app.router.lifespan_context(app):
            config = database_config(url)
            assert Tortoise.apps is not None
            assert not await MigrationAutodetector(Tortoise.apps, config["apps"]).changes(), (
                "Models changed without a checked-in migration"
            )
            executor = MigrationExecutor(Tortoise.get_connection("default"), config["apps"])
            await executor.migrate(direction="forward")
            assert not await executor.plan(), "Migration head was not reached"
            assert not await db.Namespace.exists(), "Checks require an empty disposable database"
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
                        db.ModuleFederationDistribution,
                        db.PythonDistribution,
                        db.PythonFile,
                    )
                ):
                    await model.all().delete()
                await check_import()
                print("Registry PostgreSQL migrations, transactions, HTTP and S3 checks passed.")
            finally:
                for model in (
                    db.PythonFile,
                    db.PythonDistribution,
                    db.ModuleFederationDistribution,
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
