from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..contracts.models import (
    Condition,
    ReleaseRecord,
    TargetAssociation,
    TargetManifest,
    TargetRecord,
)


class RegistryConflictError(RuntimeError):
    pass


class RegistryNotFoundError(RuntimeError):
    pass


class RegistryStateError(RuntimeError):
    pass


def _column(row: Any, name: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _target_from_row(row: Any) -> TargetRecord:
    return TargetRecord(
        target_key=_column(row, "target_key"),
        target_digest=_column(row, "target_digest"),
        artifact_format=_column(row, "artifact_format"),
        entrypoint=_column(row, "entrypoint"),
        conditions=tuple(
            Condition.model_validate(condition)
            for condition in json.loads(_column(row, "compatibility_json"))
        ),
        source_repository=_column(row, "source_repository"),
        source_revision=_column(row, "source_revision"),
        build_id=_column(row, "build_id"),
    )


@dataclass(frozen=True)
class ArtifactFile:
    blob_key: str
    media_type: str
    size: int


class RegistryRepository:
    """Thin D1/R2 adapter; package semantics stay in the service layer."""

    def __init__(self, env: Any) -> None:
        self.db = env.DB
        self.artifacts = env.ARTIFACTS

    async def authenticate(self, token_sha256: str) -> str | None:
        row = (
            await self.db.prepare(
                "SELECT c.namespace FROM credentials c JOIN namespaces n "
                "ON n.namespace = c.namespace WHERE c.token_sha256 = ?1 "
                "AND c.disabled = 0 AND n.status = 'active'"
            )
            .bind(token_sha256)
            .first()
        )
        return _column(row, "namespace")

    async def put_blob(self, digest: str, content: bytes, media_type: str) -> None:
        key = f"blobs/{digest}"
        existing = await self.artifacts.head(key)
        if existing is not None:
            if int(existing.size) != len(content):
                raise RegistryConflictError("content-addressed blob size conflict")
            return
        await self.artifacts.put(key, content, httpMetadata={"contentType": media_type})

    async def blobs_exist(self, manifest: TargetManifest) -> bool:
        for descriptor in manifest.files.values():
            stored = await self.artifacts.head(f"blobs/sha256:{descriptor.sha256}")
            if stored is None or int(stored.size) != descriptor.size:
                return False
        return True

    async def _release_state(self, namespace: str, name: str, version: str) -> str | None:
        row = (
            await self.db.prepare(
                "SELECT state FROM releases WHERE namespace = ?1 AND name = ?2 AND version = ?3"
            )
            .bind(namespace, name, version)
            .first()
        )
        return _column(row, "state")

    async def _target(
        self, namespace: str, name: str, version: str, target_key: str
    ) -> TargetRecord | None:
        row = (
            await self.db.prepare(
                "SELECT target_key, target_digest, artifact_format, entrypoint, "
                "compatibility_json, source_repository, source_revision, build_id "
                "FROM targets WHERE namespace = ?1 AND name = ?2 AND version = ?3 "
                "AND target_key = ?4"
            )
            .bind(namespace, name, version, target_key)
            .first()
        )
        return _target_from_row(row) if row is not None else None

    async def put_target(
        self,
        namespace: str,
        name: str,
        version: str,
        target_key: str,
        association: TargetAssociation,
    ) -> TargetRecord:
        manifest = association.manifest
        target_digest = manifest.digest
        existing = await self._target(namespace, name, version, target_key)
        if existing is not None:
            if existing.target_digest == target_digest:
                return existing
            raise RegistryConflictError("target key already has a different immutable digest")

        state = await self._release_state(namespace, name, version)
        if state in {"yanked", "blocked"}:
            raise RegistryStateError(f"cannot append a target to a {state} release")
        if not await self.blobs_exist(manifest):
            raise RegistryConflictError(
                "one or more target blobs are missing or have the wrong size"
            )

        manifest_json = manifest.canonical_bytes().decode("utf-8")
        await self.artifacts.put(
            f"manifests/{target_digest}",
            manifest.canonical_bytes(),
            httpMetadata={"contentType": "application/json"},
        )
        statements = [
            self.db.prepare(
                "INSERT INTO extensions(namespace, name) VALUES (?1, ?2) "
                "ON CONFLICT(namespace, name) DO NOTHING"
            ).bind(namespace, name),
            self.db.prepare(
                "INSERT INTO releases(namespace, name, version, state) "
                "VALUES (?1, ?2, ?3, 'preparing') "
                "ON CONFLICT(namespace, name, version) DO NOTHING"
            ).bind(namespace, name, version),
            self.db.prepare(
                "INSERT INTO targets(namespace, name, version, target_key, target_digest, "
                "artifact_format, entrypoint, compatibility_json, manifest_json, "
                "source_repository, source_revision, build_id) "
                "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)"
            ).bind(
                namespace,
                name,
                version,
                target_key,
                target_digest,
                manifest.artifact_format,
                manifest.entrypoint,
                json.dumps(
                    [condition.model_dump(mode="json") for condition in manifest.conditions],
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                manifest_json,
                association.source_repository,
                association.source_revision,
                association.build_id,
            ),
        ]
        try:
            await self.db.batch(statements)
        except Exception as error:
            raced = await self._target(namespace, name, version, target_key)
            if raced is not None and raced.target_digest == target_digest:
                return raced
            if raced is not None:
                raise RegistryConflictError(
                    "target key already has a different immutable digest"
                ) from error
            raise
        target = await self._target(namespace, name, version, target_key)
        if target is None:
            raise RuntimeError("target transaction committed without a readable row")
        return target

    async def publish(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        state = await self._release_state(namespace, name, version)
        if state is None:
            raise RegistryNotFoundError("release does not exist")
        if state in {"yanked", "blocked"}:
            raise RegistryStateError(f"cannot publish a {state} release")
        if state == "preparing":
            result = (
                await self.db.prepare(
                    "UPDATE releases SET state = 'published', published_at = CURRENT_TIMESTAMP "
                    "WHERE namespace = ?1 AND name = ?2 AND version = ?3 AND state = 'preparing' "
                    "AND EXISTS (SELECT 1 FROM targets WHERE namespace = ?1 AND name = ?2 "
                    "AND version = ?3)"
                )
                .bind(namespace, name, version)
                .run()
            )
            if int(result.meta.changes) != 1:
                raise RegistryStateError("release requires at least one accepted target")
        release = await self.get_release(namespace, name, version, public=False)
        if release is None:
            raise RuntimeError("published release is not readable")
        return release

    async def yank(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        result = (
            await self.db.prepare(
                "UPDATE releases SET state = 'yanked' WHERE namespace = ?1 AND name = ?2 "
                "AND version = ?3 AND state IN ('published', 'yanked')"
            )
            .bind(namespace, name, version)
            .run()
        )
        if int(result.meta.changes) == 0:
            state = await self._release_state(namespace, name, version)
            if state is None:
                raise RegistryNotFoundError("release does not exist")
            if state not in {"published", "yanked"}:
                raise RegistryStateError(f"cannot yank a {state} release")
        release = await self.get_release(namespace, name, version, public=False)
        if release is None:
            raise RegistryStateError("release cannot be yanked from its current state")
        return release

    async def get_release(
        self, namespace: str, name: str, version: str, *, public: bool = True
    ) -> ReleaseRecord | None:
        query = (
            "SELECT namespace, name, version, state FROM releases "
            "WHERE namespace = ?1 AND name = ?2 AND version = ?3"
        )
        if public:
            query += " AND state IN ('published', 'yanked', 'blocked')"
        release_row = await self.db.prepare(query).bind(namespace, name, version).first()
        if release_row is None:
            return None
        targets_result = (
            await self.db.prepare(
                "SELECT target_key, target_digest, artifact_format, entrypoint, "
                "compatibility_json, source_repository, source_revision, build_id "
                "FROM targets WHERE namespace = ?1 AND name = ?2 AND version = ?3 "
                "ORDER BY target_key"
            )
            .bind(namespace, name, version)
            .all()
        )
        targets = tuple(_target_from_row(row) for row in targets_result.results)
        return ReleaseRecord(
            namespace=_column(release_row, "namespace"),
            name=_column(release_row, "name"),
            version=_column(release_row, "version"),
            state=_column(release_row, "state"),
            targets=targets,
        )

    async def list_extensions(self) -> list[dict[str, str]]:
        result = await self.db.prepare(
            "SELECT DISTINCT e.namespace, e.name FROM extensions e "
            "JOIN releases r ON r.namespace = e.namespace AND r.name = e.name "
            "WHERE r.state = 'published' ORDER BY e.namespace, e.name"
        ).all()
        return [
            {"namespace": _column(row, "namespace"), "name": _column(row, "name")}
            for row in result.results
        ]

    async def extension_versions(self, namespace: str, name: str) -> list[ReleaseRecord]:
        result = (
            await self.db.prepare(
                "SELECT version FROM releases WHERE namespace = ?1 AND name = ?2 "
                "AND state IN ('published', 'yanked', 'blocked') ORDER BY created_at DESC"
            )
            .bind(namespace, name)
            .all()
        )
        releases: list[ReleaseRecord] = []
        for row in result.results:
            release = await self.get_release(namespace, name, _column(row, "version"))
            if release is not None:
                releases.append(release)
        return releases

    async def target_manifest(self, target_digest: str) -> TargetManifest | None:
        row = (
            await self.db.prepare(
                "SELECT t.manifest_json, r.state FROM targets t JOIN releases r "
                "ON r.namespace = t.namespace AND r.name = t.name AND r.version = t.version "
                "WHERE t.target_digest = ?1 AND r.state IN ('published', 'yanked', 'blocked') "
                "ORDER BY CASE r.state WHEN 'published' THEN 0 WHEN 'yanked' THEN 1 ELSE 2 END "
                "LIMIT 1"
            )
            .bind(target_digest)
            .first()
        )
        if row is None:
            return None
        if _column(row, "state") == "blocked":
            raise RegistryStateError("artifact is blocked")
        return TargetManifest.model_validate_json(_column(row, "manifest_json"))

    async def artifact_file(self, target_digest: str, relative_path: str) -> ArtifactFile | None:
        manifest = await self.target_manifest(target_digest)
        if manifest is None:
            return None
        descriptor = manifest.files.get(relative_path)
        if descriptor is None:
            return None
        return ArtifactFile(
            blob_key=f"blobs/sha256:{descriptor.sha256}",
            media_type=descriptor.media_type,
            size=descriptor.size,
        )
