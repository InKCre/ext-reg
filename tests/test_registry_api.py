from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import MutableMapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from inkcre_extension_registry.contracts.models import (
    Condition,
    FileDescriptor,
    TargetAssociation,
    TargetManifest,
)
from inkcre_extension_registry.service.app import create_app

PUBLISHER_TOKEN = "inkcre-first-party-publisher"
AUTHORIZATION = {"Authorization": f"Bearer {PUBLISHER_TOKEN}"}


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
        rows = [dict(row) for row in self.execute().fetchall()]
        return SimpleNamespace(results=rows)

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
async def registry(tmp_path: Path):
    del tmp_path
    migration = Path("migrations/0001_registry.sql").read_text(encoding="utf-8")
    database = _D1(migration)
    database.connection.execute(
        "INSERT INTO namespaces(namespace, display_name) VALUES (?, ?)",
        ("inkcre", "InKCre"),
    )
    database.connection.execute(
        "INSERT INTO credentials(id, namespace, token_sha256, label) VALUES (?, ?, ?, ?)",
        (
            "first-party",
            "inkcre",
            hashlib.sha256(PUBLISHER_TOKEN.encode()).hexdigest(),
            "test",
        ),
    )
    environment = SimpleNamespace(DB=database, ARTIFACTS=_R2())
    application = _WithEnvironment(create_app(), environment)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="https://registry.test",
    ) as client:
        yield client


def _association(content: bytes, api_range: str = "^2.0.0") -> TargetAssociation:
    return TargetAssociation(
        manifest=TargetManifest(
            artifact_format="module-federation-esm-v1",
            entrypoint="remoteEntry.js",
            conditions=(
                Condition(
                    key="inkcre.integration",
                    operator="equals",
                    value="module-federation-esm-v1",
                ),
                Condition(
                    key="inkcre.extension-api",
                    operator="semver",
                    value=api_range,
                ),
            ),
            files={
                "remoteEntry.js": FileDescriptor(
                    sha256=hashlib.sha256(content).hexdigest(),
                    size=len(content),
                    media_type="text/javascript",
                )
            },
        ),
        source_repository="https://github.com/InKCre/client-web",
        source_revision="a" * 40,
        build_id="test-build",
    )


@pytest.mark.asyncio
async def test_publish_append_resolve_and_yank_are_digest_locked(
    registry: httpx.AsyncClient,
) -> None:
    content = b"export default {}\n"
    blob_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    blob_path = f"/v1/blobs/{blob_digest}"

    mismatch = await registry.put(blob_path, content=b"wrong", headers=AUTHORIZATION)
    assert mismatch.status_code == 409
    uploaded = await registry.put(
        blob_path,
        content=content,
        headers=AUTHORIZATION | {"Content-Type": "text/javascript"},
    )
    assert uploaded.status_code == 204

    target_path = "/v1/extensions/inkcre/twitter/versions/0.1.0/targets/web.chrome"
    association = _association(content)
    unauthorized = await registry.put(target_path, json=association.model_dump(mode="json"))
    assert unauthorized.status_code == 401

    created = await registry.put(
        target_path,
        json=association.model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert created.status_code == 200
    target_digest = created.json()["target_digest"]

    hidden = await registry.get("/v1/extensions/inkcre/twitter/versions/0.1.0")
    assert hidden.status_code == 404

    published = await registry.post(
        "/v1/extensions/inkcre/twitter/versions/0.1.0/publish",
        headers=AUTHORIZATION,
    )
    assert published.status_code == 200
    assert published.json()["state"] == "published"

    exact = await registry.get("/v1/extensions/inkcre/twitter/versions/0.1.0")
    assert exact.status_code == 200
    assert exact.json()["targets"][0]["target_digest"] == target_digest

    manifest = await registry.get(f"/v1/artifacts/{target_digest}/manifest")
    assert manifest.status_code == 200
    assert manifest.headers["cache-control"].endswith("immutable")
    assert manifest.json()["files"]["remoteEntry.js"]["sha256"] == blob_digest.removeprefix(
        "sha256:"
    )

    duplicate = await registry.put(
        target_path,
        json=association.model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["target_digest"] == target_digest

    conflict = await registry.put(
        target_path,
        json=_association(content, api_range="^3.0.0").model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert conflict.status_code == 409

    reused = await registry.put(
        "/v1/extensions/inkcre/twitter/versions/0.1.0/targets/web.fallback",
        json=association.model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert reused.status_code == 200
    assert reused.json()["target_digest"] == target_digest

    yanked = await registry.post(
        "/v1/extensions/inkcre/twitter/versions/0.1.0/yank",
        headers=AUTHORIZATION,
    )
    assert yanked.status_code == 200
    assert yanked.json()["state"] == "yanked"

    rejected_append = await registry.put(
        "/v1/extensions/inkcre/twitter/versions/0.1.0/targets/web.after-yank",
        json=association.model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert rejected_append.status_code == 409


@pytest.mark.asyncio
async def test_namespace_credential_cannot_publish_another_namespace(
    registry: httpx.AsyncClient,
) -> None:
    response = await registry.put(
        "/v1/extensions/community/example/versions/1.0.0/targets/web.chrome",
        json=_association(b"content").model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_preparing_release_cannot_be_yanked(registry: httpx.AsyncClient) -> None:
    content = b"preparing release\n"
    blob_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    uploaded = await registry.put(
        f"/v1/blobs/{blob_digest}",
        content=content,
        headers=AUTHORIZATION,
    )
    assert uploaded.status_code == 204

    target = await registry.put(
        "/v1/extensions/inkcre/preparing/versions/0.1.0/targets/web.chrome",
        json=_association(content).model_dump(mode="json"),
        headers=AUTHORIZATION,
    )
    assert target.status_code == 200

    response = await registry.post(
        "/v1/extensions/inkcre/preparing/versions/0.1.0/yank",
        headers=AUTHORIZATION,
    )
    assert response.status_code == 409
