"""Documentation snapshot persistence and lifecycle; HTTP routing is in app.py."""

from __future__ import annotations

import hashlib
import json
from typing import cast
from urllib.parse import quote

import anyio
from inkcre_extension_toolkit.documentation import DocumentationBundle
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from ..contracts.models import (
    DocumentationPublication,
    DocumentationReceipt,
    DocumentationRecord,
    DocumentationScope,
    ReleaseDocumentation,
    ReleaseState,
)
from . import database as db
from .repository import (
    RegistryBlockedError,
    RegistryConflictError,
    RegistryNotFoundError,
    RegistryStateError,
)
from .settings import Settings
from .storage import ArtifactStore


class DocumentationPreconditionError(RuntimeError):
    pass


def readable(release: db.Release, *, public: bool = True) -> None:
    if release.state == "blocked":
        raise RegistryBlockedError("documentation Release is operator-blocked")
    if public and release.state == "preparing":
        raise RegistryNotFoundError("public documentation does not exist")


def record(
    row: db.DocumentationSet, release: db.Release, settings: Settings
) -> DocumentationRecord:
    snapshot = row.snapshot
    return DocumentationRecord(
        snapshot_id=snapshot.id,
        content_sha256=snapshot.content_sha256,
        entry=snapshot.entry,
        source_repository=snapshot.source_repository,
        source_revision=snapshot.source_revision,
        build_id=snapshot.build_id,
        scope=cast(DocumentationScope, row.scope),
        etag=f'"{snapshot.etag}"',
        entry_url=f"{settings.public_origin}/documentation/{release.extension_id}/{release.version}/{row.scope}/",
        snapshot_url=settings.documentation_origin(snapshot.id) + "/",
        updated_at=row.updated_at.isoformat(),
    )


def object_key(digest: str, path: str) -> str:
    return f"documentation/{digest}/{path}"


def static_path(snapshot: db.DocumentationSnapshot, path: str) -> tuple[str, bool]:
    """Exact files win; support directory indexes and clean HTML links, never SPA fallback."""
    if not path:
        return snapshot.entry, False
    if path in snapshot.files:
        return path, False
    directory = path.rstrip("/") + "/index.html"
    if directory in snapshot.files:
        return directory, not path.endswith("/")
    if not path.endswith("/") and path + ".html" in snapshot.files:
        return path + ".html", False
    raise RegistryNotFoundError("documentation file does not exist")


def snapshot_link(settings: Settings, snapshot_id: str, path: str) -> str:
    return settings.documentation_origin(snapshot_id) + "/" + quote(path, safe="/")


def receipt(
    snapshot: db.DocumentationSnapshot, release: db.Release, settings: Settings
) -> DocumentationReceipt:
    return DocumentationReceipt(
        name=release.extension_id,
        version=release.version,
        scope=cast(DocumentationScope, snapshot.scope),
        snapshot_id=snapshot.id,
        content_sha256=snapshot.content_sha256,
        entry=snapshot.entry,
        source_repository=snapshot.source_repository,
        source_revision=snapshot.source_revision,
        build_id=snapshot.build_id,
        snapshot_etag=f'"{snapshot.etag}"',
        snapshot_url=settings.documentation_origin(snapshot.id) + "/",
        committed_at=snapshot.created_at.isoformat(),
    )


class DocumentationRepository:
    """Own documentation queries, atomic pointer replacement, and bounded object staging."""

    def __init__(self, artifacts: ArtifactStore) -> None:
        self._artifacts = artifacts
        self._capacity = anyio.CapacityLimiter(4)

    async def discover(
        self, extension: str, version: str, settings: Settings, *, public: bool = True
    ) -> ReleaseDocumentation:
        release = await db.Release.filter(extension_id=extension, version=version).first()
        if release is None:
            raise RegistryNotFoundError("Release does not exist")
        readable(release, public=public)
        rows = (
            await db.DocumentationSet.filter(release=release)
            .select_related("snapshot")
            .order_by("scope")
        )
        return ReleaseDocumentation(
            name=extension,
            version=version,
            state=cast(ReleaseState, release.state),
            sets=[record(row, release, settings) for row in rows],
        )

    async def public_snapshot(self, snapshot_id: str) -> db.DocumentationSnapshot:
        snapshot = (
            await db.DocumentationSnapshot.filter(id=snapshot_id).select_related("release").first()
        )
        if snapshot is None:
            raise RegistryNotFoundError("documentation snapshot does not exist")
        readable(snapshot.release)
        return snapshot

    async def publish(
        self,
        extension: str,
        version: str,
        scope: DocumentationScope,
        payload: DocumentationPublication,
        bundle: DocumentationBundle,
        settings: Settings,
    ) -> DocumentationReceipt:
        if bundle.digest != payload.content_sha256:
            raise RegistryConflictError("documentation content digest does not match metadata")
        metadata = payload.model_dump(mode="json")
        etag = hashlib.sha256(
            json.dumps(
                {**metadata, "name": extension, "version": version, "scope": scope},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        async def check(
            release: db.Release,
        ) -> db.DocumentationSet | db.DocumentationSnapshot | None:
            readable(release, public=False)
            association = {
                "python": db.PythonDistribution,
                "module-federation": db.ModuleFederationDistribution,
            }.get(scope)
            if association is not None and not await association.filter(release=release).exists():
                raise RegistryStateError(
                    "documentation scope requires its Distribution association"
                )
            previous = await db.DocumentationSnapshot.filter(id=payload.snapshot_id).first()
            if previous is not None:
                # The ETag fingerprints target, metadata and original precondition.
                # Confirming this commit never reactivates its historical snapshot.
                if previous.etag != etag:
                    raise RegistryConflictError(
                        "snapshot identity belongs to a different publication"
                    )
                return previous
            current = (
                await db.DocumentationSet.filter(release=release, scope=scope)
                .select_related("snapshot")
                .first()
            )
            if (payload.expected_etag is None and current is not None) or (
                payload.expected_etag is not None
                and (current is None or payload.expected_etag != f'"{current.snapshot.etag}"')
            ):
                raise DocumentationPreconditionError(
                    "documentation changed; read it before replacing"
                )
            return current

        release = await db.Release.filter(extension_id=extension, version=version).first()
        if release is None:
            raise RegistryNotFoundError("Release does not exist")
        existing = await check(release)
        if isinstance(existing, db.DocumentationSnapshot):
            return receipt(existing, release, settings)
        paths = iter(bundle.files)
        failure: Exception | None = None

        async def stage() -> None:
            nonlocal failure
            try:
                for path in paths:
                    async with self._capacity:
                        key = object_key(bundle.digest, path)
                        stored = await self._artifacts.head(key)
                        if stored is None:
                            await self._artifacts.put(
                                key,
                                bundle.files[path],
                                content_type=bundle.manifest[path]["media_type"],
                            )
                        elif stored.size != len(bundle.files[path]):
                            raise RegistryConflictError(
                                "documentation staging object size conflict"
                            )
            except Exception as error:
                failure = failure or error
                group.cancel_scope.cancel()

        async with anyio.create_task_group() as group:
            for _ in range(min(4, len(bundle.files))):
                group.start_soon(stage)
        if failure is not None:
            raise failure
        try:
            async with in_transaction():
                release = await db.Release.filter(id=release.id).select_for_update().get()
                current = await check(release)
                if isinstance(current, db.DocumentationSnapshot):
                    return receipt(current, release, settings)
                snapshot = await db.DocumentationSnapshot.create(
                    id=payload.snapshot_id,
                    release=release,
                    scope=scope,
                    **{
                        key: value
                        for key, value in metadata.items()
                        if key not in {"snapshot_id", "expected_etag"}
                    },
                    files=bundle.manifest,
                    etag=etag,
                )
                if current is None:
                    current = await db.DocumentationSet.create(
                        release=release, scope=scope, snapshot=snapshot
                    )
                else:
                    current.snapshot = snapshot
                    await current.save(update_fields=["snapshot_id", "updated_at"])
        except IntegrityError as error:
            raise RegistryConflictError(
                "documentation snapshot address is already bound"
            ) from error
        return receipt(snapshot, release, settings)
