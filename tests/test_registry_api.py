from __future__ import annotations

import base64
import hashlib
import io
import json
import sqlite3
import zipfile
from collections.abc import AsyncIterator, MutableMapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from inkcre_extension_registry.service.app import create_app

PUBLISHER_TOKEN = "inkcre-first-party-publisher"
AUTHORIZATION = {"Authorization": f"Bearer {PUBLISHER_TOKEN}"}
BASIC_AUTHORIZATION = {
    "Authorization": "Basic " + base64.b64encode(f"__token__:{PUBLISHER_TOKEN}".encode()).decode()
}


class _Statement:
    def __init__(self, database: _D1, sql: str) -> None:
        self.database = database
        self.sql = sql
        self.parameters: tuple[Any, ...] = ()

    def bind(self, *parameters: Any) -> _Statement:
        self.parameters = parameters
        return self

    def execute(self) -> sqlite3.Cursor:
        return self.database.connection.execute(self.sql, self.parameters)

    async def first(self) -> dict[str, Any] | None:
        row = self.execute().fetchone()
        return dict(row) if row is not None else None

    async def all(self) -> SimpleNamespace:
        return SimpleNamespace(results=[dict(row) for row in self.execute().fetchall()])

    async def run(self) -> SimpleNamespace:
        cursor = self.execute()
        return SimpleNamespace(meta=SimpleNamespace(changes=max(cursor.rowcount, 0)))


class _D1:
    def __init__(self, migration: str) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(migration)

    def prepare(self, sql: str) -> _Statement:
        return _Statement(self, sql)

    async def batch(self, statements: list[_Statement]) -> list[SimpleNamespace]:
        results: list[SimpleNamespace] = []
        self.connection.execute("BEGIN")
        try:
            for statement in statements:
                cursor = statement.execute()
                results.append(
                    SimpleNamespace(meta=SimpleNamespace(changes=max(cursor.rowcount, 0)))
                )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return results


class _R2Object:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.size = len(body)


class _R2:
    def __init__(self) -> None:
        self.objects: dict[str, _R2Object] = {}

    async def head(self, key: str) -> _R2Object | None:
        return self.objects.get(key)

    async def get(self, key: str) -> _R2Object | None:
        return self.objects.get(key)

    async def put(self, key: str, body: bytes, **_options: Any) -> _R2Object:
        stored = _R2Object(body)
        self.objects[key] = stored
        return stored


class _WithEnvironment:
    def __init__(self, application: Any, environment: Any) -> None:
        self.application = application
        self.environment = environment

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        scope["env"] = self.environment
        await self.application(scope, receive, send)


@pytest.fixture
async def registry() -> AsyncIterator[tuple[httpx.AsyncClient, _D1, _R2]]:
    migration = Path("migrations/0001_registry.sql").read_text(encoding="utf-8")
    database = _D1(migration)
    database.connection.execute("INSERT INTO namespaces(name) VALUES (?)", ("inkcre",))
    database.connection.execute(
        "INSERT INTO credentials(token_hash, namespace, label) VALUES (?, ?, ?)",
        (hashlib.sha256(PUBLISHER_TOKEN.encode()).hexdigest(), "inkcre", "test"),
    )
    artifacts = _R2()
    environment = SimpleNamespace(
        DB=database,
        ARTIFACTS=artifacts,
        PUBLIC_ORIGIN="https://registry.test",
    )
    application = _WithEnvironment(create_app(), environment)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="https://registry.test",
    ) as client:
        yield client, database, artifacts


def _python_prepare(version: str = "0.1.1") -> dict[str, object]:
    return {
        "nickname": "Twitter",
        "version": version,
        "python": {
            "project": "inkcre-ext-twitter",
            "host_sdk": "core-py",
            "host_sdk_version": ">=0.1.0 <0.2.0",
            "entry_point": {
                "group": "inkcre.core.extensions",
                "name": "twitter",
                "object": "extensions.twitter:Extension",
            },
            "source_repository": "https://github.com/InKCre/core-py",
            "source_revision": "a" * 40,
            "build_id": "test-build",
        },
    }


def _wheel(version: str = "0.1.1", *, marker: bytes = b"") -> tuple[str, bytes, bytes]:
    filename = f"inkcre_ext_twitter-{version}-py3-none-any.whl"
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: inkcre-ext-twitter\n"
        f"Version: {version}\n"
        "Requires-Python: >=3.12,<3.14\n"
        "\n"
    ).encode()
    entries = b"[inkcre.core.extensions]\ntwitter = extensions.twitter:Extension\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        dist_info = f"inkcre_ext_twitter-{version}.dist-info"
        archive.writestr(f"{dist_info}/METADATA", metadata)
        archive.writestr(f"{dist_info}/entry_points.txt", entries)
        archive.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\nTag: py3-none-any\n")
        archive.writestr("extensions/twitter.py", b"class Extension: pass\n" + marker)
    return filename, buffer.getvalue(), metadata


def _legacy_files(
    filename: str,
    wheel: bytes,
    *,
    version: str = "0.1.1",
    digest: str | None = None,
) -> dict[str, tuple[str | None, bytes | str, str | None]]:
    return {
        ":action": (None, "file_upload", None),
        "protocol_version": (None, "1", None),
        "metadata_version": (None, "2.4", None),
        "name": (None, "inkcre-ext-twitter", None),
        "version": (None, version, None),
        "filetype": (None, "bdist_wheel", None),
        "pyversion": (None, "py3", None),
        "sha256_digest": (None, digest or hashlib.sha256(wheel).hexdigest(), None),
        "content": (filename, wheel, "application/octet-stream"),
    }


def _mf_archive(*, missing: str | None = None, marker: str = "") -> bytes:
    manifest = {
        "id": "twitter",
        "name": "twitter",
        "metaData": {
            "publicPath": "./",
            "remoteEntry": {"path": "", "name": "remoteEntry.js", "type": "module"},
        },
        "shared": [
            {
                "name": "@inkcre/core",
                "assets": {
                    "js": {"sync": ["assets/core.js"], "async": []},
                    "css": {"sync": [], "async": []},
                },
            }
        ],
        "exposes": [
            {
                "name": "./extension",
                "assets": {
                    "js": {"sync": ["assets/extension.js"], "async": []},
                    "css": {"sync": ["assets/extension.css"], "async": []},
                },
            }
        ],
    }
    files = {
        "mf-manifest.json": json.dumps(manifest).encode(),
        "remoteEntry.js": f"export default {{}};{marker}\n".encode(),
        "assets/core.js": b"export const core = {};\n",
        "assets/extension.js": b"export const extension = {};\n",
        "assets/extension.css": b".extension {}\n",
    }
    if missing:
        files.pop(missing)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_python_prepare_upload_publish_simple_yank_and_unyank(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, _database, _artifacts = registry
    release_path = "/v1/extensions/inkcre/twitter/releases/0.1.1"
    prepared = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare(),
        headers=AUTHORIZATION,
    )
    assert prepared.status_code == 200
    assert prepared.json() == {
        "name": "inkcre/twitter",
        "nickname": "Twitter",
        "version": "0.1.1",
        "state": "preparing",
        "python": {
            "project": "inkcre-ext-twitter",
            "simple_url": "/simple/inkcre-ext-twitter/",
            "host_sdk": "core-py",
            "host_sdk_version": ">=0.1.0 <0.2.0",
            "entry_point": {
                "group": "inkcre.core.extensions",
                "name": "twitter",
                "object": "extensions.twitter:Extension",
            },
        },
        "module_federation": None,
    }
    duplicate_prepare = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare(),
        headers=AUTHORIZATION,
    )
    assert duplicate_prepare.status_code == 200
    preparing_exact = await client.get(release_path)
    assert preparing_exact.status_code == 404
    assert preparing_exact.headers["cache-control"] == "no-store"
    assert (await client.post(release_path + "/publish", headers=AUTHORIZATION)).status_code == 409

    filename, wheel, metadata = _wheel()
    uploaded = await client.post(
        "/legacy/", files=_legacy_files(filename, wheel), headers=BASIC_AUTHORIZATION
    )
    assert uploaded.status_code == 200, uploaded.text
    retry = await client.post(
        "/legacy/", files=_legacy_files(filename, wheel), headers=BASIC_AUTHORIZATION
    )
    assert retry.status_code == 200
    _filename, conflicting_wheel, _metadata = _wheel(marker=b"# changed\n")
    conflict = await client.post(
        "/legacy/",
        files=_legacy_files(filename, conflicting_wheel),
        headers=BASIC_AUTHORIZATION,
    )
    assert conflict.status_code == 409
    hidden_simple = await client.get("/simple/inkcre-ext-twitter/")
    assert hidden_simple.status_code == 404
    assert hidden_simple.headers["cache-control"] == "no-store"
    hidden_package = await client.get(f"/packages/inkcre-ext-twitter/0.1.1/{filename}")
    assert hidden_package.status_code == 404
    assert hidden_package.headers["cache-control"] == "no-store"

    published = await client.post(release_path + "/publish", headers=AUTHORIZATION)
    assert published.status_code == 200
    assert published.json()["state"] == "published"
    assert (await client.post(release_path + "/publish", headers=AUTHORIZATION)).status_code == 200

    exact = await client.get(release_path)
    assert exact.status_code == 200
    assert exact.headers["cache-control"] == "no-store"
    assert exact.json()["python"]["entry_point"]["object"] == "extensions.twitter:Extension"

    catalog = await client.get("/")
    assert catalog.status_code == 200
    assert catalog.headers["content-type"].startswith("text/html")
    assert catalog.headers["cache-control"] == "no-store"
    assert catalog.headers["content-security-policy"].startswith("default-src 'none'")
    assert '<span class="nickname">Twitter</span>' in catalog.text
    assert '<span class="name">inkcre/twitter</span>' in catalog.text
    assert 'href="/v1/extensions/inkcre/twitter"' in catalog.text

    appended = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json={
            "nickname": "Twitter",
            "version": "0.1.1",
            "module_federation": {
                "host_sdk": "@inkcre/core",
                "host_sdk_version": ">=0.1.0 <0.2.0",
                "source_repository": "https://github.com/InKCre/client-web",
                "source_revision": "b" * 40,
                "build_id": "web-build",
            },
        },
        headers=AUTHORIZATION,
    )
    assert appended.status_code == 200
    assert appended.json()["module_federation"] is not None
    assert (await client.get(release_path)).json()["module_federation"] is None
    uploaded_mf = await client.post(
        release_path + "/module-federation",
        files={"content": ("remote.zip", _mf_archive(), "application/zip")},
        headers=AUTHORIZATION,
    )
    assert uploaded_mf.status_code == 200
    assert (await client.get(release_path)).json()["module_federation"] is not None

    simple_json = await client.get(
        "/simple/inkcre-ext-twitter/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    )
    assert simple_json.status_code == 200
    assert simple_json.headers["content-type"].startswith("application/vnd.pypi.simple.v1+json")
    assert simple_json.headers["vary"] == "Accept"
    assert simple_json.headers["cache-control"] == "no-store"
    file_record = simple_json.json()["files"][0]
    assert file_record["hashes"] == {"sha256": hashlib.sha256(wheel).hexdigest()}
    assert file_record["core-metadata"] == {"sha256": hashlib.sha256(metadata).hexdigest()}
    assert file_record["yanked"] is False
    simple_root = await client.get(
        "/simple/", headers={"Accept": "application/vnd.pypi.simple.v1+json"}
    )
    assert simple_root.json() == {
        "meta": {"api-version": "1.1"},
        "projects": [{"name": "inkcre-ext-twitter"}],
    }
    assert simple_root.headers["cache-control"] == "no-store"

    simple_html = await client.get(
        "/simple/inkcre-ext-twitter/",
        headers={"Accept": "application/vnd.pypi.simple.v1+html"},
    )
    assert simple_html.status_code == 200
    assert simple_html.headers["content-type"].startswith("application/vnd.pypi.simple.v1+html")
    assert simple_html.headers["cache-control"] == "no-store"
    assert 'data-core-metadata="sha256=' in simple_html.text
    package_path = f"/packages/inkcre-ext-twitter/0.1.1/{filename}"
    package = await client.get(package_path)
    assert package.content == wheel
    assert package.headers["cache-control"].endswith("immutable")
    assert (await client.get(package_path + ".metadata")).content == metadata

    yanked = await client.post(
        release_path + "/yank",
        json={"reason": "broken dependency"},
        headers=AUTHORIZATION,
    )
    assert yanked.status_code == 200
    assert yanked.json()["state"] == "yanked"
    assert (await client.get(release_path)).status_code == 200
    assert (await client.get(package_path)).content == wheel
    assert (await client.get("/v1/extensions")).json() == []
    assert "No Extensions published yet." in (await client.get("/")).text
    yanked_simple = await client.get(
        "/simple/inkcre-ext-twitter/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    )
    assert yanked_simple.json()["files"][0]["yanked"] == "broken dependency"
    conflicting_yank = await client.post(
        release_path + "/yank",
        json={"reason": "another reason"},
        headers=AUTHORIZATION,
    )
    assert conflicting_yank.status_code == 409

    unyanked = await client.post(release_path + "/unyank", headers=AUTHORIZATION)
    assert unyanked.status_code == 200
    assert unyanked.json()["state"] == "published"
    assert (await client.post(release_path + "/unyank", headers=AUTHORIZATION)).status_code == 200


@pytest.mark.asyncio
async def test_module_federation_snapshot_is_closed_absolute_and_immutable(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, _database, artifacts = registry
    prepare = {
        "nickname": "Twitter",
        "version": "0.2.0",
        "module_federation": {
            "host_sdk": "@inkcre/core",
            "host_sdk_version": ">=0.1.0 <0.2.0",
            "source_repository": "https://github.com/InKCre/client-web",
            "source_revision": "b" * 40,
            "build_id": "web-build",
        },
    }
    response = await client.post(
        "/v1/extensions/inkcre/twitter/releases", json=prepare, headers=AUTHORIZATION
    )
    assert response.status_code == 200
    release_path = "/v1/extensions/inkcre/twitter/releases/0.2.0"
    upload_path = release_path + "/module-federation"
    missing = await client.post(
        upload_path,
        files={"content": ("remote.zip", _mf_archive(missing="assets/core.js"))},
        headers=AUTHORIZATION,
    )
    assert missing.status_code == 400
    assert artifacts.objects == {}
    preparing_exact = await client.get(release_path)
    assert preparing_exact.status_code == 404
    assert preparing_exact.headers["cache-control"] == "no-store"
    hidden_asset = await client.get(
        "/extensions/inkcre/twitter/0.2.0/module-federation/remoteEntry.js"
    )
    assert hidden_asset.status_code == 404
    assert hidden_asset.headers["cache-control"] == "no-store"

    archive = _mf_archive()
    uploaded = await client.post(
        upload_path,
        files={"content": ("remote.zip", archive, "application/zip")},
        headers=AUTHORIZATION,
    )
    assert uploaded.status_code == 200, uploaded.text
    retry = await client.post(
        upload_path,
        files={"content": ("remote.zip", archive, "application/zip")},
        headers=AUTHORIZATION | {"Host": "alternate-uploader.test"},
    )
    assert retry.status_code == 200
    conflict = await client.post(
        upload_path,
        files={"content": ("remote.zip", _mf_archive(marker="// changed"))},
        headers=AUTHORIZATION,
    )
    assert conflict.status_code == 409
    assert (await client.post(release_path + "/publish", headers=AUTHORIZATION)).status_code == 200

    manifest_path = "/extensions/inkcre/twitter/0.2.0/module-federation/mf-manifest.json"
    manifest = await client.get(manifest_path)
    assert manifest.status_code == 200
    assert manifest.headers["access-control-allow-origin"] == "*"
    assert manifest.headers["cache-control"].endswith("immutable")
    assert manifest.json()["metaData"]["publicPath"] == (
        "https://registry.test/extensions/inkcre/twitter/0.2.0/module-federation/"
    )
    asset = await client.get(
        "/extensions/inkcre/twitter/0.2.0/module-federation/assets/extension.js"
    )
    assert asset.status_code == 200
    assert asset.headers["content-type"].startswith("text/javascript")


@pytest.mark.asyncio
async def test_native_associations_own_independent_immutable_provenance(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, _database, _artifacts = registry
    python = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare("0.3.0"),
        headers=AUTHORIZATION,
    )
    assert python.status_code == 200
    module_federation = {
        "nickname": "Twitter",
        "version": "0.3.0",
        "module_federation": {
            "host_sdk": "@inkcre/core",
            "host_sdk_version": ">=0.1.0 <0.2.0",
            "source_repository": "https://github.com/InKCre/client-web",
            "source_revision": "b" * 40,
            "build_id": "web-build",
        },
    }
    appended = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=module_federation,
        headers=AUTHORIZATION,
    )
    assert appended.status_code == 200
    assert appended.json()["python"] is not None
    assert appended.json()["module_federation"] is not None
    conflicting_retry = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json={
            **module_federation,
            "module_federation": {
                **module_federation["module_federation"],
                "source_revision": "c" * 40,
            },
        },
        headers=AUTHORIZATION,
    )
    assert conflicting_retry.status_code == 409


@pytest.mark.asyncio
async def test_python_prerelease_uses_lossless_native_pep440_project_version(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, _database, _artifacts = registry
    prepared = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare("0.4.0-rc.1"),
        headers=AUTHORIZATION,
    )
    assert prepared.status_code == 200
    filename, wheel, _metadata = _wheel("0.4.0rc1")
    uploaded = await client.post(
        "/legacy/",
        files=_legacy_files(filename, wheel, version="0.4.0rc1"),
        headers=BASIC_AUTHORIZATION,
    )
    assert uploaded.status_code == 200, uploaded.text
    release_path = "/v1/extensions/inkcre/twitter/releases/0.4.0-rc.1"
    published = await client.post(release_path + "/publish", headers=AUTHORIZATION)
    assert published.status_code == 200
    simple = await client.get(
        "/simple/inkcre-ext-twitter/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    )
    assert simple.status_code == 200
    assert simple.json()["files"][0]["url"].startswith("/packages/inkcre-ext-twitter/0.4.0rc1/")


@pytest.mark.parametrize(
    ("release_version", "wheel_version", "form_alias"),
    [
        ("0.5.0", "0.5.0", "0.5.0.0"),
        ("0.5.0-rc.1", "0.5.0rc1", "0.5.0rc01"),
    ],
)
@pytest.mark.asyncio
async def test_legacy_form_version_rejects_pep440_aliases(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
    release_version: str,
    wheel_version: str,
    form_alias: str,
) -> None:
    client, _database, _artifacts = registry
    prepared = await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare(release_version),
        headers=AUTHORIZATION,
    )
    assert prepared.status_code == 200
    filename, wheel, _metadata = _wheel(wheel_version)
    rejected = await client.post(
        "/legacy/",
        files=_legacy_files(filename, wheel, version=form_alias),
        headers=BASIC_AUTHORIZATION,
    )
    assert rejected.status_code == 400
    assert "canonical PEP 440 spelling" in rejected.text


@pytest.mark.asyncio
async def test_publish_rechecks_every_ready_r2_object_before_d1_visibility(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, _database, artifacts = registry
    await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare(),
        headers=AUTHORIZATION,
    )
    filename, wheel, _metadata = _wheel()
    uploaded = await client.post(
        "/legacy/", files=_legacy_files(filename, wheel), headers=BASIC_AUTHORIZATION
    )
    assert uploaded.status_code == 200
    archive_key = next(key for key in artifacts.objects if key.startswith("staging/python/"))
    artifacts.objects.pop(archive_key)
    release_path = "/v1/extensions/inkcre/twitter/releases/0.1.1"
    publish = await client.post(release_path + "/publish", headers=AUTHORIZATION)
    assert publish.status_code == 409
    assert (await client.get(release_path)).status_code == 404
    repaired = await client.post(
        "/legacy/", files=_legacy_files(filename, wheel), headers=BASIC_AUTHORIZATION
    )
    assert repaired.status_code == 200
    assert (await client.post(release_path + "/publish", headers=AUTHORIZATION)).status_code == 200


@pytest.mark.asyncio
async def test_upload_bounds_auth_and_operator_block(
    registry: tuple[httpx.AsyncClient, _D1, _R2],
) -> None:
    client, database, _artifacts = registry
    unauthorized = await client.post(
        "/v1/extensions/inkcre/twitter/releases", json=_python_prepare()
    )
    assert unauthorized.status_code == 401
    another_namespace = await client.post(
        "/v1/extensions/community/twitter/releases",
        json=_python_prepare(),
        headers=AUTHORIZATION,
    )
    assert another_namespace.status_code == 403
    wrong_basic = {
        "Authorization": "Basic "
        + base64.b64encode(f"publisher:{PUBLISHER_TOKEN}".encode()).decode()
    }
    assert (await client.post("/legacy/", content=b"x", headers=wrong_basic)).status_code == 401
    assert (
        await client.post("/legacy/", content=b"x", headers={"Authorization": "Basic ???"})
    ).status_code == 401

    async def body() -> AsyncIterator[bytes]:
        yield b"chunked"

    chunked = await client.post(
        "/legacy/",
        content=body(),
        headers=BASIC_AUTHORIZATION | {"Transfer-Encoding": "chunked"},
    )
    assert chunked.status_code == 411
    oversize = await client.post(
        "/legacy/",
        content=b"x",
        headers=BASIC_AUTHORIZATION | {"Content-Length": str(20 * 1024 * 1024 + 1)},
    )
    assert oversize.status_code == 413

    await client.post(
        "/v1/extensions/inkcre/twitter/releases",
        json=_python_prepare(),
        headers=AUTHORIZATION,
    )
    filename, wheel, _metadata = _wheel()
    await client.post("/legacy/", files=_legacy_files(filename, wheel), headers=BASIC_AUTHORIZATION)
    release_path = "/v1/extensions/inkcre/twitter/releases/0.1.1"
    await client.post(release_path + "/publish", headers=AUTHORIZATION)
    database.connection.execute(
        "UPDATE releases SET state = 'blocked' WHERE extension_name = ? AND version = ?",
        ("inkcre/twitter", "0.1.1"),
    )
    blocked_release = await client.get(release_path)
    assert blocked_release.status_code == 451
    assert blocked_release.headers["cache-control"] == "no-store"
    package_path = f"/packages/inkcre-ext-twitter/0.1.1/{filename}"
    blocked_package = await client.get(package_path)
    assert blocked_package.status_code == 451
    assert blocked_package.headers["cache-control"] == "no-store"

    missing_release = await client.get("/v1/extensions/inkcre/missing/releases/0.1.1")
    assert missing_release.status_code == 404
    assert missing_release.headers["cache-control"] == "no-store"
