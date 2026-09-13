from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from inkcre_extension_toolkit.simple import PythonFileRecord
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from ..contracts.models import (
    ExtensionRecord,
    ExtensionSummary,
    ModuleFederationAssociationInput,
    ModuleFederationDistribution,
    PrepareReleaseRequest,
    PublisherRelease,
    PublisherWorkspace,
    PythonAssociationInput,
    PythonDistribution,
    PythonEntryPoint,
    ReleaseRecord,
    ReleaseState,
    normalize_project_name,
    python_project_version,
)
from . import database as db
from .storage import ArtifactStore


class RegistryConflictError(RuntimeError):
    pass


class RegistryNotFoundError(RuntimeError):
    pass


class RegistryStateError(RuntimeError):
    pass


class RegistryBlockedError(RegistryStateError):
    pass


@dataclass(frozen=True)
class PreparedPythonDistribution:
    release_id: int
    extension_name: str
    release_version: str
    normalized_project: str
    project_version: str
    host_sdk: str
    host_sdk_range: str
    entry_group: str
    entry_name: str
    entry_object: str
    state: str


@dataclass(frozen=True)
class PublicObject:
    r2_key: str
    media_type: str
    etag: str


def _python_file(
    row: db.PythonFile, distribution: db.PythonDistribution, yank_reason: str | None = None
) -> PythonFileRecord:
    return PythonFileRecord(
        normalized_project=distribution.normalized_project,
        project_version=distribution.project_version,
        filename=row.filename,
        sha256=row.sha256,
        size=row.size,
        filetype=row.filetype,
        requires_python=row.requires_python,
        core_metadata_sha256=row.core_metadata_sha256,
        r2_key=row.r2_key,
        metadata_r2_key=row.metadata_r2_key,
        uploaded_at=row.uploaded_at.isoformat(),
        yank_reason=yank_reason,
    )


def _prepared_python(row: db.PythonDistribution) -> PreparedPythonDistribution:
    return PreparedPythonDistribution(
        release_id=row.release.pk,
        extension_name=row.release.extension.name,
        release_version=row.release.version,
        normalized_project=row.normalized_project,
        project_version=row.project_version,
        host_sdk=row.host_sdk,
        host_sdk_range=row.host_sdk_range,
        entry_group=row.entry_group,
        entry_name=row.entry_name,
        entry_object=row.entry_object,
        state=row.release.state,
    )


def _release_query():
    return (
        db.Release.all()
        .select_related("extension")
        .prefetch_related("python", "python__files", "module_federation")
    )


def _descriptor(row: db.Release, *, public: bool) -> ReleaseRecord:
    python_row = row.python
    mf_row = row.module_federation
    python = None
    if python_row is not None and (not public or bool(list(python_row.files))):
        python = PythonDistribution(
            project=python_row.normalized_project,
            simple_url=f"/simple/{python_row.normalized_project}/",
            host_sdk=cast(Literal["core-py"], python_row.host_sdk),
            host_sdk_version=python_row.host_sdk_range,
            entry_point=PythonEntryPoint(
                group=python_row.entry_group,
                name=python_row.entry_name,
                object=python_row.entry_object,
            ),
        )
    module_federation = None
    if mf_row is not None and (not public or mf_row.manifest_r2_key is not None):
        module_federation = ModuleFederationDistribution(
            manifest_url=f"/extensions/{row.extension.name}/{row.version}/module-federation/mf-manifest.json",
            host_sdk=cast(Literal["@inkcre/core"], mf_row.host_sdk),
            host_sdk_version=mf_row.host_sdk_range,
        )
    return ReleaseRecord(
        name=row.extension.name,
        nickname=row.extension.nickname,
        version=row.version,
        state=cast(ReleaseState, row.state),
        python=python,
        module_federation=module_federation,
    )


def _python_values(association: PythonAssociationInput) -> dict:
    return {
        "normalized_project": normalize_project_name(association.project),
        "host_sdk": association.host_sdk,
        "host_sdk_range": association.host_sdk_version,
        "entry_group": association.entry_point.group,
        "entry_name": association.entry_point.name,
        "entry_object": association.entry_point.object,
        "source_repository": association.source_repository,
        "source_revision": association.source_revision,
        "build_id": association.build_id,
    }


def _mf_values(association: ModuleFederationAssociationInput) -> dict:
    return {
        "host_sdk": association.host_sdk,
        "host_sdk_range": association.host_sdk_version,
        "source_repository": association.source_repository,
        "source_revision": association.source_revision,
        "build_id": association.build_id,
    }


class RegistryRepository:
    """Registry operations own short database transactions; R2 staging precedes them."""

    def __init__(self, artifacts: ArtifactStore) -> None:
        self.artifacts = artifacts

    async def authenticate(self, token_hash: str) -> str | None:
        row = (
            await db.Credential.filter(
                token_hash=token_hash, disabled=False, namespace__status="active"
            )
            .select_related("namespace")
            .first()
        )
        return row.namespace.name if row else None

    async def prepare_release(
        self, namespace: str, name: str, request: PrepareReleaseRequest
    ) -> ReleaseRecord:
        extension_name = f"{namespace}/{name}"
        try:
            async with in_transaction():
                # Serialize creation of the publisher's extension identity. Release locks
                # below are shared with every association/state-changing operation.
                await db.Namespace.filter(name=namespace).select_for_update().get()
                extension, _created = await db.Extension.get_or_create(
                    name=extension_name,
                    defaults={"namespace_id": namespace, "nickname": request.nickname},
                )
                if extension.nickname != request.nickname:
                    raise RegistryConflictError("Extension nickname is immutable")
                release, _created = await db.Release.get_or_create(
                    extension=extension, version=request.version
                )
                release = await db.Release.filter(pk=release.pk).select_for_update().get()
                for model, association, values, label in (
                    (
                        db.PythonDistribution,
                        request.python,
                        _python_values(request.python) if request.python else {},
                        "Python",
                    ),
                    (
                        db.ModuleFederationDistribution,
                        request.module_federation,
                        _mf_values(request.module_federation) if request.module_federation else {},
                        "Module Federation",
                    ),
                ):
                    if association is None:
                        continue
                    existing = await model.filter(release=release).first()
                    if existing is not None:
                        if any(getattr(existing, key) != value for key, value in values.items()):
                            raise RegistryConflictError(f"{label} association is immutable")
                    else:
                        if release.state not in {"preparing", "published"}:
                            raise RegistryStateError(
                                f"cannot append an association to a {release.state} release"
                            )
                        if model is db.PythonDistribution:
                            values["project_version"] = python_project_version(request.version)
                        await model.create(release=release, **values)
        except IntegrityError as error:
            raise RegistryConflictError(
                "Release association conflicts with existing data"
            ) from error
        result = await self.get_release(extension_name, request.version, public=False)
        assert result is not None
        return result

    async def get_release(
        self, extension_name: str, version: str, *, public: bool = True
    ) -> ReleaseRecord | None:
        row = await _release_query().filter(extension_id=extension_name, version=version).first()
        if row is None or (public and row.state == "preparing"):
            return None
        if public and row.state == "blocked":
            raise RegistryBlockedError("Release is operator-blocked")
        return _descriptor(row, public=public)

    async def publisher_workspace(self, namespace: str, offset: int) -> PublisherWorkspace:
        rows = (
            await _release_query()
            .filter(extension__namespace_id=namespace)
            .order_by("-created_at", "extension_id", "-version")
            .offset(offset)
            .limit(11)
        )
        records = [
            PublisherRelease(
                **_descriptor(row, public=False).model_dump(),
                python_uploaded=row.python is not None and bool(list(row.python.files)),
                web_uploaded=(
                    row.module_federation is not None
                    and row.module_federation.manifest_r2_key is not None
                ),
            )
            for row in rows[:10]
        ]
        return PublisherWorkspace(
            namespace=namespace,
            releases=tuple(records),
            offset=offset,
            next_offset=offset + 10 if len(rows) > 10 else None,
        )

    async def list_extensions(self) -> list[ExtensionSummary]:
        rows = await db.Extension.filter(releases__state="published").distinct().order_by("name")
        return [ExtensionSummary(name=row.name, nickname=row.nickname) for row in rows]

    async def get_extension(self, extension_name: str) -> ExtensionRecord | None:
        rows = (
            await _release_query()
            .filter(extension_id=extension_name, state="published")
            .order_by("-created_at", "-version")
        )
        if not rows:
            return None
        return ExtensionRecord(
            name=extension_name,
            nickname=rows[0].extension.nickname,
            releases=tuple(_descriptor(row, public=True) for row in rows),
        )

    async def _locked_release(self, extension_name: str, version: str) -> db.Release:
        row = (
            await db.Release.filter(extension_id=extension_name, version=version)
            .select_for_update()
            .first()
        )
        if row is None:
            raise RegistryNotFoundError("Release does not exist")
        return row

    async def publish(self, extension_name: str, version: str) -> ReleaseRecord:
        row = await _release_query().filter(extension_id=extension_name, version=version).first()
        if row is None:
            raise RegistryNotFoundError("Release does not exist")
        if row.state in {"yanked", "blocked"}:
            raise RegistryStateError(f"cannot publish a {row.state} Release")
        # Network checks never hold a database transaction/connection lock.
        if row.state == "preparing" and not await self._release_objects_available(row):
            raise RegistryStateError(
                "Release native Distribution objects are not completely available"
            )
        async with in_transaction():
            locked = await self._locked_release(extension_name, version)
            if locked.state in {"yanked", "blocked"}:
                raise RegistryStateError(f"cannot publish a {locked.state} Release")
            if locked.state == "preparing":
                locked.state = "published"
                locked.yank_reason = None
                locked.published_at = datetime.now(UTC)
                locked.updated_at = locked.published_at
                await locked.save(
                    update_fields=["state", "yank_reason", "published_at", "updated_at"]
                )
        result = await self.get_release(extension_name, version)
        assert result is not None
        return result

    async def _release_objects_available(self, row: db.Release) -> bool:
        files = list(row.python.files) if row.python is not None else []
        for file in files:
            archive = await self.artifacts.head(file.r2_key)
            metadata = await self.artifacts.head(file.metadata_r2_key)
            if archive is None or archive.size != file.size or metadata is None:
                return False
        mf = row.module_federation
        mf_ready = mf is not None and mf.manifest_r2_key is not None
        if mf is not None and mf.manifest_r2_key is not None:
            prefix = mf.manifest_r2_key.removesuffix("mf-manifest.json")
            for path in mf.asset_paths:
                if await self.artifacts.head(prefix + path) is None:
                    return False
        return bool(files or mf_ready)

    async def yank(self, extension_name: str, version: str, reason: str) -> ReleaseRecord:
        async with in_transaction():
            row = await self._locked_release(extension_name, version)
            if row.state == "yanked":
                if row.yank_reason != reason:
                    raise RegistryConflictError("Yank reason conflicts with the existing yank")
            elif row.state == "published":
                row.state, row.yank_reason, row.updated_at = "yanked", reason, datetime.now(UTC)
                await row.save(update_fields=["state", "yank_reason", "updated_at"])
            else:
                raise RegistryStateError(f"cannot yank a {row.state} Release")
        result = await self.get_release(extension_name, version)
        assert result is not None
        return result

    async def unyank(self, extension_name: str, version: str) -> ReleaseRecord:
        async with in_transaction():
            row = await self._locked_release(extension_name, version)
            if row.state == "yanked":
                row.state, row.yank_reason, row.updated_at = "published", None, datetime.now(UTC)
                await row.save(update_fields=["state", "yank_reason", "updated_at"])
            elif row.state != "published":
                raise RegistryStateError(f"cannot unyank a {row.state} Release")
        result = await self.get_release(extension_name, version)
        assert result is not None
        return result

    async def prepared_python_distribution(
        self, namespace: str, normalized_project: str, project_version: str
    ) -> PreparedPythonDistribution | None:
        row = (
            await db.PythonDistribution.filter(
                release__extension__namespace_id=namespace,
                normalized_project=normalized_project,
                project_version=project_version,
            )
            .select_related("release__extension")
            .first()
        )
        return _prepared_python(row) if row is not None else None

    async def prepared_python_distributions(
        self, namespace: str, normalized_project: str
    ) -> list[PreparedPythonDistribution]:
        rows = await db.PythonDistribution.filter(
            release__extension__namespace_id=namespace, normalized_project=normalized_project
        ).select_related("release__extension")
        return [_prepared_python(row) for row in rows]

    async def _ensure_object(self, key: str, content: bytes, media_type: str) -> None:
        stored = await self.artifacts.head(key)
        if stored is not None and stored.size != len(content):
            raise RegistryConflictError("Distribution staging object size conflict")
        if stored is None:
            await self.artifacts.put(key, content, content_type=media_type)

    async def put_python_file(
        self,
        distribution: PreparedPythonDistribution,
        *,
        filename: str,
        content: bytes,
        sha256: str,
        filetype: str,
        requires_python: str | None,
        metadata: bytes,
        metadata_sha256: str,
    ) -> PythonFileRecord:
        if distribution.state not in {"preparing", "published"}:
            raise RegistryStateError(
                f"cannot append a Python file to a {distribution.state} Release"
            )
        existing = await db.PythonFile.filter(
            distribution__release_id=distribution.release_id, filename=filename
        ).first()
        if existing is not None and (
            existing.sha256 != sha256
            or existing.size != len(content)
            or existing.core_metadata_sha256 != metadata_sha256
        ):
            raise RegistryConflictError("Python filename already has different immutable bytes")
        r2_key = existing.r2_key if existing else f"staging/python/{sha256}/{filename}"
        metadata_key = (
            existing.metadata_r2_key
            if existing
            else f"staging/python-metadata/{metadata_sha256}.metadata"
        )
        await self._ensure_object(r2_key, content, "application/octet-stream")
        await self._ensure_object(metadata_key, metadata, "application/octet-stream")
        try:
            async with in_transaction():
                release = await self._locked_release(
                    distribution.extension_name, distribution.release_version
                )
                if release.state not in {"preparing", "published"}:
                    raise RegistryStateError(
                        f"cannot append a Python file to a {release.state} Release"
                    )
                python = await db.PythonDistribution.get(release_id=distribution.release_id)
                row, _created = await db.PythonFile.get_or_create(
                    distribution=python,
                    filename=filename,
                    defaults={
                        "sha256": sha256,
                        "size": len(content),
                        "filetype": filetype,
                        "requires_python": requires_python,
                        "core_metadata_sha256": metadata_sha256,
                        "r2_key": r2_key,
                        "metadata_r2_key": metadata_key,
                    },
                )
                if (
                    row.sha256 != sha256
                    or row.size != len(content)
                    or row.core_metadata_sha256 != metadata_sha256
                ):
                    raise RegistryConflictError(
                        "Python filename already has different immutable bytes"
                    )
        except IntegrityError as error:
            raise RegistryConflictError(
                "Python file conflicts with an existing distribution"
            ) from error
        return _python_file(row, python)

    async def simple_projects(self) -> list[str]:
        rows = (
            await db.PythonDistribution.filter(
                release__state__in=("published", "yanked"), files__id__isnull=False
            )
            .distinct()
            .order_by("normalized_project")
            .values("normalized_project")
        )
        return [row["normalized_project"] for row in rows]

    async def simple_files(self, normalized_project: str) -> list[PythonFileRecord]:
        rows = (
            await db.PythonFile.filter(
                distribution__normalized_project=normalized_project,
                distribution__release__state__in=("published", "yanked"),
            )
            .select_related("distribution__release")
            .order_by("filename")
        )
        return [
            _python_file(
                row,
                row.distribution,
                row.distribution.release.yank_reason
                if row.distribution.release.state == "yanked"
                else None,
            )
            for row in rows
        ]

    async def python_public_file(
        self,
        normalized_project: str,
        project_version: str,
        filename: str,
        *,
        metadata: bool = False,
    ) -> PublicObject | None:
        row = (
            await db.PythonFile.filter(
                distribution__normalized_project=normalized_project,
                distribution__project_version=project_version,
                filename=filename,
                distribution__release__state__in=("published", "yanked", "blocked"),
            )
            .select_related("distribution__release")
            .first()
        )
        if row is None:
            return None
        if row.distribution.release.state == "blocked":
            raise RegistryBlockedError("Python Distribution is operator-blocked")
        return PublicObject(
            r2_key=row.metadata_r2_key if metadata else row.r2_key,
            media_type="application/octet-stream",
            etag=row.core_metadata_sha256 if metadata else row.sha256,
        )

    async def put_module_federation_snapshot(
        self,
        extension_name: str,
        version: str,
        snapshot_hash: str,
        files: dict[str, bytes],
        media_types: dict[str, str],
    ) -> ReleaseRecord:
        row = (
            await db.ModuleFederationDistribution.filter(
                release__extension_id=extension_name, release__version=version
            )
            .select_related("release")
            .first()
        )
        if row is None:
            raise RegistryNotFoundError("prepared Module Federation association does not exist")
        if row.internal_snapshot_hash is not None and row.internal_snapshot_hash != snapshot_hash:
            raise RegistryConflictError(
                "Module Federation association already has another snapshot"
            )
        if row.internal_snapshot_hash is None and row.release.state not in {
            "preparing",
            "published",
        }:
            raise RegistryStateError(f"cannot upload a snapshot to a {row.release.state} Release")
        prefix = f"staging/module-federation/{extension_name}/{version}/{snapshot_hash}/"
        for path, content in sorted(files.items()):
            await self._ensure_object(prefix + path, content, media_types[path])
        async with in_transaction():
            release = await self._locked_release(extension_name, version)
            current = await db.ModuleFederationDistribution.get(release=release)
            if current.internal_snapshot_hash is not None:
                if current.internal_snapshot_hash != snapshot_hash:
                    raise RegistryConflictError(
                        "Module Federation association already has another snapshot"
                    )
            else:
                if release.state not in {"preparing", "published"}:
                    raise RegistryStateError(
                        f"cannot upload a snapshot to a {release.state} Release"
                    )
                current.manifest_r2_key = prefix + "mf-manifest.json"
                current.asset_paths = sorted(files)
                current.internal_snapshot_hash = snapshot_hash
                current.uploaded_at = datetime.now(UTC)
                await current.save(
                    update_fields=[
                        "manifest_r2_key",
                        "asset_paths",
                        "internal_snapshot_hash",
                        "uploaded_at",
                    ]
                )
        result = await self.get_release(extension_name, version, public=False)
        assert result is not None
        return result

    async def module_federation_public_file(
        self, extension_name: str, version: str, relative_path: str, media_type: str
    ) -> PublicObject | None:
        row = (
            await db.ModuleFederationDistribution.filter(
                release__extension_id=extension_name,
                release__version=version,
                manifest_r2_key__isnull=False,
                release__state__in=("published", "yanked", "blocked"),
            )
            .select_related("release")
            .first()
        )
        if row is None:
            return None
        if row.release.state == "blocked":
            raise RegistryBlockedError("Module Federation Distribution is operator-blocked")
        if relative_path not in row.asset_paths:
            return None
        assert row.manifest_r2_key is not None and row.internal_snapshot_hash is not None
        return PublicObject(
            r2_key=row.manifest_r2_key.removesuffix("mf-manifest.json") + relative_path,
            media_type=media_type,
            etag=row.internal_snapshot_hash,
        )
