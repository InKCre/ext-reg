from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from inkcre_extension_toolkit.simple import PythonFileRecord
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.sql import ClauseElement

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
    normalize_project_name,
    python_project_version,
)
from . import database as db


class RegistryConflictError(RuntimeError):
    pass


class RegistryNotFoundError(RuntimeError):
    pass


class RegistryStateError(RuntimeError):
    pass


class RegistryBlockedError(RegistryStateError):
    pass


def _column(row: Any, name: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _results(result: Any) -> list[Any]:
    return list(_column(result, "results", []))


@dataclass(frozen=True)
class PreparedPythonDistribution:
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


def _python_file(row: Any) -> PythonFileRecord:
    return PythonFileRecord(
        normalized_project=_column(row, "normalized_project"),
        project_version=_column(row, "project_version"),
        filename=_column(row, "filename"),
        sha256=_column(row, "sha256"),
        size=int(_column(row, "size")),
        filetype=_column(row, "filetype"),
        requires_python=_column(row, "requires_python"),
        core_metadata_sha256=_column(row, "core_metadata_sha256"),
        r2_key=_column(row, "r2_key"),
        metadata_r2_key=_column(row, "metadata_r2_key"),
        uploaded_at=_column(row, "uploaded_at"),
        yank_reason=_column(row, "yank_reason"),
    )


def _prepared_python(row: Any) -> PreparedPythonDistribution:
    return PreparedPythonDistribution(
        extension_name=_column(row, "extension_name"),
        release_version=_column(row, "release_version"),
        normalized_project=_column(row, "normalized_project"),
        project_version=_column(row, "project_version"),
        host_sdk=_column(row, "host_sdk"),
        host_sdk_range=_column(row, "host_sdk_range"),
        entry_group=_column(row, "entry_group"),
        entry_name=_column(row, "entry_name"),
        entry_object=_column(row, "entry_object"),
        state=_column(row, "state"),
    )


class RegistryRepository:
    """D1/R2 authority for immutable native Distribution associations."""

    def __init__(self, env: Any) -> None:
        self.db = env.DB
        self.artifacts = env.ARTIFACTS

    def _prepare(self, statement: ClauseElement) -> Any:
        sql, parameters = db.compile_d1(statement)
        prepared = self.db.prepare(sql)
        return prepared.bind(*parameters) if parameters else prepared

    async def authenticate(self, token_hash: str) -> str | None:
        row = await self._prepare(
            select(db.credentials.c.namespace)
            .join(db.namespaces)
            .where(
                db.credentials.c.token_hash == token_hash,
                db.credentials.c.disabled == 0,
                db.namespaces.c.status == "active",
            )
        ).first()
        return _column(row, "namespace")

    async def _extension_row(self, extension_name: str) -> Any:
        return await self._prepare(
            select(db.extensions.c.name, db.extensions.c.namespace, db.extensions.c.nickname).where(
                db.extensions.c.name == extension_name
            )
        ).first()

    async def _release_row(self, extension_name: str, version: str) -> Any:
        return await self._prepare(
            select(
                db.extensions.c.nickname,
                db.releases.c.extension_name,
                db.releases.c.version,
                db.releases.c.state,
                db.releases.c.yank_reason,
                db.releases.c.created_at,
            )
            .select_from(db.releases.join(db.extensions))
            .where(db.releases.c.extension_name == extension_name, db.releases.c.version == version)
        ).first()

    async def _python_row(self, extension_name: str, version: str) -> Any:
        return await self._prepare(
            select(db.python_distributions).where(
                db.python_distributions.c.extension_name == extension_name,
                db.python_distributions.c.release_version == version,
            )
        ).first()

    async def _module_federation_row(self, extension_name: str, version: str) -> Any:
        return await self._prepare(
            select(db.module_federation_distributions).where(
                db.module_federation_distributions.c.extension_name == extension_name,
                db.module_federation_distributions.c.release_version == version,
            )
        ).first()

    async def _python_project_owner(self, normalized_project: str, version: str) -> str | None:
        row = await self._prepare(
            select(db.python_distributions.c.extension_name).where(
                db.python_distributions.c.normalized_project == normalized_project,
                db.python_distributions.c.project_version == version,
            )
        ).first()
        return _column(row, "extension_name")

    @staticmethod
    def _python_matches(row: Any, association: PythonAssociationInput) -> bool:
        return bool(
            row
            and _column(row, "normalized_project") == normalize_project_name(association.project)
            and _column(row, "host_sdk") == association.host_sdk
            and _column(row, "host_sdk_range") == association.host_sdk_version
            and _column(row, "entry_group") == association.entry_point.group
            and _column(row, "entry_name") == association.entry_point.name
            and _column(row, "entry_object") == association.entry_point.object
            and _column(row, "source_repository") == association.source_repository
            and _column(row, "source_revision") == association.source_revision
            and _column(row, "build_id") == association.build_id
        )

    @staticmethod
    def _mf_matches(row: Any, association: ModuleFederationAssociationInput) -> bool:
        return bool(
            row
            and _column(row, "host_sdk") == association.host_sdk
            and _column(row, "host_sdk_range") == association.host_sdk_version
            and _column(row, "source_repository") == association.source_repository
            and _column(row, "source_revision") == association.source_revision
            and _column(row, "build_id") == association.build_id
        )

    async def prepare_release(
        self,
        namespace: str,
        name: str,
        request: PrepareReleaseRequest,
    ) -> ReleaseRecord:
        extension_name = f"{namespace}/{name}"
        extension = await self._extension_row(extension_name)
        if extension is not None and _column(extension, "nickname") != request.nickname:
            raise RegistryConflictError("Extension nickname is immutable")

        release = await self._release_row(extension_name, request.version)
        python_row = await self._python_row(extension_name, request.version)
        mf_row = await self._module_federation_row(extension_name, request.version)
        if (
            request.python is not None
            and python_row is not None
            and not self._python_matches(python_row, request.python)
        ):
            raise RegistryConflictError("Python association is immutable")
        if (
            request.module_federation is not None
            and mf_row is not None
            and not self._mf_matches(mf_row, request.module_federation)
        ):
            raise RegistryConflictError("Module Federation association is immutable")

        adds_python = request.python is not None and python_row is None
        adds_mf = request.module_federation is not None and mf_row is None
        if adds_python and request.python is not None:
            owner = await self._python_project_owner(
                normalize_project_name(request.python.project),
                python_project_version(request.version),
            )
            if owner is not None and owner != extension_name:
                raise RegistryConflictError(
                    "Python Project/version already belongs to another Extension Release"
                )
        if release is not None and (adds_python or adds_mf):
            state = _column(release, "state")
            if state not in {"preparing", "published"}:
                raise RegistryStateError(f"cannot append an association to a {state} release")

        statements = [
            self._prepare(
                insert(db.extensions)
                .values(name=extension_name, namespace=namespace, nickname=request.nickname)
                .on_conflict_do_nothing(index_elements=[db.extensions.c.name])
            ),
            self._prepare(
                insert(db.releases)
                .values(extension_name=extension_name, version=request.version)
                .on_conflict_do_nothing(
                    index_elements=[db.releases.c.extension_name, db.releases.c.version]
                )
            ),
        ]
        if adds_python and request.python is not None:
            statements.append(
                self._prepare(
                    insert(db.python_distributions).values(
                        extension_name=extension_name,
                        release_version=request.version,
                        normalized_project=normalize_project_name(request.python.project),
                        project_version=python_project_version(request.version),
                        host_sdk=request.python.host_sdk,
                        host_sdk_range=request.python.host_sdk_version,
                        entry_group=request.python.entry_point.group,
                        entry_name=request.python.entry_point.name,
                        entry_object=request.python.entry_point.object,
                        source_repository=request.python.source_repository,
                        source_revision=request.python.source_revision,
                        build_id=request.python.build_id,
                    )
                )
            )
        if adds_mf and request.module_federation is not None:
            statements.append(
                self._prepare(
                    insert(db.module_federation_distributions).values(
                        extension_name=extension_name,
                        release_version=request.version,
                        host_sdk=request.module_federation.host_sdk,
                        host_sdk_range=request.module_federation.host_sdk_version,
                        source_repository=request.module_federation.source_repository,
                        source_revision=request.module_federation.source_revision,
                        build_id=request.module_federation.build_id,
                    )
                )
            )
        try:
            await self.db.batch(statements)
        except Exception as error:
            # Translate races and uniqueness collisions into the public immutable-slot contract.
            current = await self._release_row(extension_name, request.version)
            if current is not None:
                raise RegistryConflictError(
                    "Release association conflicts with existing data"
                ) from error
            if adds_python:
                raise RegistryConflictError(
                    "Python Project/version conflicts with an existing association"
                ) from error
            raise

        prepared = await self.get_release(extension_name, request.version, public=False)
        if prepared is None:
            raise RuntimeError("prepared Release transaction is not readable")
        return prepared

    async def get_release(
        self, extension_name: str, version: str, *, public: bool = True
    ) -> ReleaseRecord | None:
        row = await self._release_row(extension_name, version)
        if row is None:
            return None
        state = _column(row, "state")
        if public:
            if state == "preparing":
                return None
            if state == "blocked":
                raise RegistryBlockedError("Release is operator-blocked")

        python_row = await self._python_row(extension_name, version)
        if public and python_row is not None:
            file_row = await self._prepare(
                select(db.python_files.c.filename)
                .where(
                    db.python_files.c.normalized_project
                    == _column(python_row, "normalized_project"),
                    db.python_files.c.project_version == _column(python_row, "project_version"),
                )
                .limit(1)
            ).first()
            if file_row is None:
                python_row = None
        mf_row = await self._module_federation_row(extension_name, version)
        if public and mf_row is not None and _column(mf_row, "manifest_r2_key") is None:
            mf_row = None

        python = None
        if python_row is not None:
            project = _column(python_row, "normalized_project")
            python = PythonDistribution(
                project=project,
                simple_url=f"/simple/{project}/",
                host_sdk=_column(python_row, "host_sdk"),
                host_sdk_version=_column(python_row, "host_sdk_range"),
                entry_point=PythonEntryPoint(
                    group=_column(python_row, "entry_group"),
                    name=_column(python_row, "entry_name"),
                    object=_column(python_row, "entry_object"),
                ),
            )
        module_federation = None
        if mf_row is not None and (not public or _column(mf_row, "manifest_r2_key") is not None):
            module_federation = ModuleFederationDistribution(
                manifest_url=(
                    f"/extensions/{extension_name}/{version}/module-federation/mf-manifest.json"
                ),
                host_sdk=_column(mf_row, "host_sdk"),
                host_sdk_version=_column(mf_row, "host_sdk_range"),
            )
        return ReleaseRecord(
            name=extension_name,
            nickname=_column(row, "nickname"),
            version=version,
            state=state,
            python=python,
            module_federation=module_federation,
        )

    async def publisher_workspace(self, namespace: str, offset: int) -> PublisherWorkspace:
        # Ten records keep the existing descriptor reads within D1's per-request query budget.
        result = await self._prepare(
            select(
                db.releases.c.extension_name,
                db.releases.c.version,
                select(db.python_files.c.filename)
                .select_from(db.python_distributions.join(db.python_files))
                .where(
                    db.python_distributions.c.extension_name == db.releases.c.extension_name,
                    db.python_distributions.c.release_version == db.releases.c.version,
                )
                .exists()
                .label("python_uploaded"),
                select(db.module_federation_distributions.c.extension_name)
                .where(
                    db.module_federation_distributions.c.extension_name
                    == db.releases.c.extension_name,
                    db.module_federation_distributions.c.release_version == db.releases.c.version,
                    db.module_federation_distributions.c.manifest_r2_key.is_not(None),
                )
                .exists()
                .label("web_uploaded"),
            )
            .select_from(db.releases.join(db.extensions))
            .where(db.extensions.c.namespace == namespace)
            .order_by(
                db.releases.c.created_at.desc(),
                db.releases.c.extension_name,
                db.releases.c.version.desc(),
            )
            .limit(11)
            .offset(offset)
        ).all()
        rows = _results(result)
        releases = []
        for row in rows[:10]:
            release = await self.get_release(
                _column(row, "extension_name"), _column(row, "version"), public=False
            )
            if release is not None:
                releases.append(
                    PublisherRelease(
                        **release.model_dump(),
                        python_uploaded=bool(_column(row, "python_uploaded")),
                        web_uploaded=bool(_column(row, "web_uploaded")),
                    )
                )
        return PublisherWorkspace(
            namespace=namespace,
            releases=tuple(releases),
            offset=offset,
            next_offset=offset + 10 if len(rows) > 10 else None,
        )

    async def list_extensions(self) -> list[ExtensionSummary]:
        result = await self._prepare(
            select(db.extensions.c.name, db.extensions.c.nickname)
            .where(
                select(db.releases.c.extension_name)
                .where(
                    db.releases.c.extension_name == db.extensions.c.name,
                    db.releases.c.state == "published",
                )
                .exists()
            )
            .order_by(db.extensions.c.name)
        ).all()
        return [
            ExtensionSummary(name=_column(row, "name"), nickname=_column(row, "nickname"))
            for row in _results(result)
        ]

    async def get_extension(self, extension_name: str) -> ExtensionRecord | None:
        extension = await self._extension_row(extension_name)
        if extension is None:
            return None
        versions = await self._prepare(
            select(db.releases.c.version)
            .where(
                db.releases.c.extension_name == extension_name,
                db.releases.c.state == "published",
            )
            .order_by(db.releases.c.created_at.desc(), db.releases.c.version.desc())
        ).all()
        releases: list[ReleaseRecord] = []
        for row in _results(versions):
            release = await self.get_release(extension_name, _column(row, "version"))
            if release is not None:
                releases.append(release)
        if not releases:
            return None
        return ExtensionRecord(
            name=extension_name,
            nickname=_column(extension, "nickname"),
            releases=tuple(releases),
        )

    async def publish(self, extension_name: str, version: str) -> ReleaseRecord:
        row = await self._release_row(extension_name, version)
        if row is None:
            raise RegistryNotFoundError("Release does not exist")
        state = _column(row, "state")
        if state in {"yanked", "blocked"}:
            raise RegistryStateError(f"cannot publish a {state} Release")
        if state == "preparing":
            if not await self._release_objects_available(extension_name, version):
                raise RegistryStateError(
                    "Release native Distribution objects are not completely available"
                )
            result = await self._prepare(
                update(db.releases)
                .values(
                    state="published",
                    yank_reason=None,
                    published_at=func.current_timestamp(),
                    updated_at=func.current_timestamp(),
                )
                .where(
                    db.releases.c.extension_name == extension_name,
                    db.releases.c.version == version,
                    db.releases.c.state == "preparing",
                    or_(
                        select(db.python_files.c.filename)
                        .select_from(db.python_distributions.join(db.python_files))
                        .where(
                            db.python_distributions.c.extension_name == extension_name,
                            db.python_distributions.c.release_version == version,
                        )
                        .exists(),
                        select(db.module_federation_distributions.c.extension_name)
                        .where(
                            db.module_federation_distributions.c.extension_name == extension_name,
                            db.module_federation_distributions.c.release_version == version,
                            db.module_federation_distributions.c.manifest_r2_key.is_not(None),
                        )
                        .exists(),
                    ),
                )
            ).run()
            if int(_column(_column(result, "meta"), "changes", 0)) != 1:
                raise RegistryStateError(
                    "Release requires at least one validated native Distribution"
                )
        published = await self.get_release(extension_name, version)
        if published is None:
            raise RuntimeError("published Release is not readable")
        return published

    async def _release_objects_available(self, extension_name: str, version: str) -> bool:
        python_result = await self._prepare(
            select(
                db.python_files.c.r2_key, db.python_files.c.metadata_r2_key, db.python_files.c.size
            )
            .join(db.python_distributions)
            .where(
                db.python_distributions.c.extension_name == extension_name,
                db.python_distributions.c.release_version == version,
            )
        ).all()
        python_rows = _results(python_result)
        for row in python_rows:
            archive = await self.artifacts.head(_column(row, "r2_key"))
            metadata = await self.artifacts.head(_column(row, "metadata_r2_key"))
            if archive is None or int(archive.size) != int(_column(row, "size")):
                return False
            if metadata is None:
                return False

        mf_row = await self._module_federation_row(extension_name, version)
        mf_ready = mf_row is not None and _column(mf_row, "manifest_r2_key") is not None
        if mf_ready:
            manifest_key = _column(mf_row, "manifest_r2_key")
            prefix = manifest_key.removesuffix("mf-manifest.json")
            paths = json.loads(_column(mf_row, "asset_paths_json"))
            for relative_path in paths:
                if await self.artifacts.head(prefix + relative_path) is None:
                    return False
        return bool(python_rows or mf_ready)

    async def yank(self, extension_name: str, version: str, reason: str) -> ReleaseRecord:
        row = await self._release_row(extension_name, version)
        if row is None:
            raise RegistryNotFoundError("Release does not exist")
        state = _column(row, "state")
        if state == "yanked":
            if _column(row, "yank_reason") != reason:
                raise RegistryConflictError("Yank reason conflicts with the existing yank")
        elif state == "published":
            await self._prepare(
                update(db.releases)
                .values(state="yanked", yank_reason=reason, updated_at=func.current_timestamp())
                .where(
                    db.releases.c.extension_name == extension_name,
                    db.releases.c.version == version,
                    db.releases.c.state == "published",
                )
            ).run()
        else:
            raise RegistryStateError(f"cannot yank a {state} Release")
        yanked = await self.get_release(extension_name, version)
        if yanked is None:
            raise RuntimeError("yanked Release is not readable")
        return yanked

    async def unyank(self, extension_name: str, version: str) -> ReleaseRecord:
        row = await self._release_row(extension_name, version)
        if row is None:
            raise RegistryNotFoundError("Release does not exist")
        state = _column(row, "state")
        if state == "yanked":
            await self._prepare(
                update(db.releases)
                .values(state="published", yank_reason=None, updated_at=func.current_timestamp())
                .where(
                    db.releases.c.extension_name == extension_name,
                    db.releases.c.version == version,
                    db.releases.c.state == "yanked",
                )
            ).run()
        elif state != "published":
            raise RegistryStateError(f"cannot unyank a {state} Release")
        published = await self.get_release(extension_name, version)
        if published is None:
            raise RuntimeError("unyanked Release is not readable")
        return published

    async def prepared_python_distribution(
        self, namespace: str, normalized_project: str, project_version: str
    ) -> PreparedPythonDistribution | None:
        row = await self._prepare(
            select(db.python_distributions, db.releases.c.state)
            .select_from(db.python_distributions.join(db.releases).join(db.extensions))
            .where(
                db.extensions.c.namespace == namespace,
                db.python_distributions.c.normalized_project == normalized_project,
                db.python_distributions.c.project_version == project_version,
            )
        ).first()
        return _prepared_python(row) if row is not None else None

    async def prepared_python_distributions(
        self, namespace: str, normalized_project: str
    ) -> list[PreparedPythonDistribution]:
        result = await self._prepare(
            select(db.python_distributions, db.releases.c.state)
            .select_from(db.python_distributions.join(db.releases).join(db.extensions))
            .where(
                db.extensions.c.namespace == namespace,
                db.python_distributions.c.normalized_project == normalized_project,
            )
        ).all()
        return [_prepared_python(row) for row in _results(result)]

    async def _python_file_row(
        self, normalized_project: str, project_version: str, filename: str
    ) -> Any:
        return await self._prepare(
            select(db.python_files).where(
                db.python_files.c.normalized_project == normalized_project,
                db.python_files.c.project_version == project_version,
                db.python_files.c.filename == filename,
            )
        ).first()

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
        existing = await self._python_file_row(
            distribution.normalized_project, distribution.project_version, filename
        )
        if existing is not None:
            record = _python_file(existing)
            if (
                record.sha256 == sha256
                and record.size == len(content)
                and record.core_metadata_sha256 == metadata_sha256
            ):
                stored = await self.artifacts.head(record.r2_key)
                if stored is not None and int(stored.size) != len(content):
                    raise RegistryConflictError("Python staging object size conflict")
                if stored is None:
                    await self.artifacts.put(
                        record.r2_key,
                        content,
                        httpMetadata={"contentType": "application/octet-stream"},
                    )
                metadata_stored = await self.artifacts.head(record.metadata_r2_key)
                if metadata_stored is not None and int(metadata_stored.size) != len(metadata):
                    raise RegistryConflictError("Core Metadata staging object size conflict")
                if metadata_stored is None:
                    await self.artifacts.put(
                        record.metadata_r2_key,
                        metadata,
                        httpMetadata={"contentType": "application/octet-stream"},
                    )
                return record
            raise RegistryConflictError("Python filename already has different immutable bytes")

        r2_key = f"staging/python/{sha256}/{filename}"
        metadata_r2_key = f"staging/python-metadata/{metadata_sha256}.metadata"
        stored = await self.artifacts.head(r2_key)
        if stored is not None and int(stored.size) != len(content):
            raise RegistryConflictError("Python staging object size conflict")
        if stored is None:
            await self.artifacts.put(
                r2_key, content, httpMetadata={"contentType": "application/octet-stream"}
            )
        metadata_stored = await self.artifacts.head(metadata_r2_key)
        if metadata_stored is not None and int(metadata_stored.size) != len(metadata):
            raise RegistryConflictError("Core Metadata staging object size conflict")
        if metadata_stored is None:
            await self.artifacts.put(
                metadata_r2_key,
                metadata,
                httpMetadata={"contentType": "application/octet-stream"},
            )
        try:
            await self._prepare(
                insert(db.python_files).values(
                    normalized_project=distribution.normalized_project,
                    project_version=distribution.project_version,
                    filename=filename,
                    sha256=sha256,
                    size=len(content),
                    filetype=filetype,
                    requires_python=requires_python,
                    core_metadata_sha256=metadata_sha256,
                    r2_key=r2_key,
                    metadata_r2_key=metadata_r2_key,
                )
            ).run()
        except Exception as error:
            raced = await self._python_file_row(
                distribution.normalized_project, distribution.project_version, filename
            )
            if raced is not None:
                record = _python_file(raced)
                if (
                    record.sha256 == sha256
                    and record.size == len(content)
                    and record.core_metadata_sha256 == metadata_sha256
                ):
                    return record
                raise RegistryConflictError(
                    "Python filename already has different immutable bytes"
                ) from error
            raise
        row = await self._python_file_row(
            distribution.normalized_project, distribution.project_version, filename
        )
        if row is None:
            raise RuntimeError("accepted Python file is not readable")
        return _python_file(row)

    async def simple_projects(self) -> list[str]:
        result = await self._prepare(
            select(db.python_distributions.c.normalized_project)
            .distinct()
            .select_from(db.python_distributions.join(db.releases).join(db.python_files))
            .where(db.releases.c.state.in_(("published", "yanked")))
            .order_by(db.python_distributions.c.normalized_project)
        ).all()
        return [_column(row, "normalized_project") for row in _results(result)]

    async def simple_files(self, normalized_project: str) -> list[PythonFileRecord]:
        result = await self._prepare(
            select(
                db.python_files,
                case(
                    (db.releases.c.state == "yanked", db.releases.c.yank_reason), else_=None
                ).label("yank_reason"),
            )
            .select_from(db.python_files.join(db.python_distributions).join(db.releases))
            .where(
                db.python_files.c.normalized_project == normalized_project,
                db.releases.c.state.in_(("published", "yanked")),
            )
            .order_by(db.python_files.c.filename)
        ).all()
        return [_python_file(row) for row in _results(result)]

    async def python_public_file(
        self,
        normalized_project: str,
        project_version: str,
        filename: str,
        *,
        metadata: bool = False,
    ) -> PublicObject | None:
        row = await self._prepare(
            select(db.python_files, db.releases.c.state)
            .select_from(db.python_files.join(db.python_distributions).join(db.releases))
            .where(
                db.python_files.c.normalized_project == normalized_project,
                db.python_files.c.project_version == project_version,
                db.python_files.c.filename == filename,
                db.releases.c.state.in_(("published", "yanked", "blocked")),
            )
        ).first()
        if row is None:
            return None
        if _column(row, "state") == "blocked":
            raise RegistryBlockedError("Python Distribution is operator-blocked")
        if metadata:
            return PublicObject(
                r2_key=_column(row, "metadata_r2_key"),
                media_type="application/octet-stream",
                etag=_column(row, "core_metadata_sha256"),
            )
        return PublicObject(
            r2_key=_column(row, "r2_key"),
            media_type="application/octet-stream",
            etag=_column(row, "sha256"),
        )

    async def put_module_federation_snapshot(
        self,
        extension_name: str,
        version: str,
        snapshot_hash: str,
        files: dict[str, bytes],
        media_types: dict[str, str],
    ) -> ReleaseRecord:
        row = await self._module_federation_row(extension_name, version)
        if row is None:
            raise RegistryNotFoundError("prepared Module Federation association does not exist")
        release = await self._release_row(extension_name, version)
        state = _column(release, "state")
        existing_hash = _column(row, "internal_snapshot_hash")
        prefix = f"staging/module-federation/{extension_name}/{version}/{snapshot_hash}/"
        if existing_hash is not None:
            if existing_hash == snapshot_hash:
                for relative_path, content in sorted(files.items()):
                    key = prefix + relative_path
                    stored = await self.artifacts.head(key)
                    if stored is not None and int(stored.size) != len(content):
                        raise RegistryConflictError(
                            "Module Federation staging object size conflict"
                        )
                    if stored is None:
                        await self.artifacts.put(
                            key,
                            content,
                            httpMetadata={"contentType": media_types[relative_path]},
                        )
                result = await self.get_release(extension_name, version, public=False)
                if result is None:
                    raise RuntimeError("Module Federation association is not readable")
                return result
            raise RegistryConflictError(
                "Module Federation association already has another snapshot"
            )
        if state not in {"preparing", "published"}:
            raise RegistryStateError(f"cannot upload a snapshot to a {state} Release")

        for relative_path, content in sorted(files.items()):
            key = prefix + relative_path
            stored = await self.artifacts.head(key)
            if stored is not None:
                if int(stored.size) != len(content):
                    raise RegistryConflictError("Module Federation staging object size conflict")
                continue
            await self.artifacts.put(
                key,
                content,
                httpMetadata={"contentType": media_types[relative_path]},
            )
        manifest_key = prefix + "mf-manifest.json"
        result = await self._prepare(
            update(db.module_federation_distributions)
            .values(
                manifest_r2_key=manifest_key,
                asset_paths_json=json.dumps(sorted(files), separators=(",", ":")),
                internal_snapshot_hash=snapshot_hash,
                uploaded_at=func.current_timestamp(),
            )
            .where(
                db.module_federation_distributions.c.extension_name == extension_name,
                db.module_federation_distributions.c.release_version == version,
                db.module_federation_distributions.c.manifest_r2_key.is_(None),
            )
        ).run()
        if int(_column(_column(result, "meta"), "changes", 0)) != 1:
            raced = await self._module_federation_row(extension_name, version)
            if _column(raced, "internal_snapshot_hash") != snapshot_hash:
                raise RegistryConflictError(
                    "Module Federation association already has another snapshot"
                )
        association = await self.get_release(extension_name, version, public=False)
        if association is None:
            raise RuntimeError("accepted Module Federation snapshot is not readable")
        return association

    async def module_federation_public_file(
        self, extension_name: str, version: str, relative_path: str, media_type: str
    ) -> PublicObject | None:
        row = await self._prepare(
            select(
                db.module_federation_distributions.c.manifest_r2_key,
                db.module_federation_distributions.c.asset_paths_json,
                db.module_federation_distributions.c.internal_snapshot_hash,
                db.releases.c.state,
            )
            .select_from(db.module_federation_distributions.join(db.releases))
            .where(
                db.module_federation_distributions.c.extension_name == extension_name,
                db.module_federation_distributions.c.release_version == version,
                db.module_federation_distributions.c.manifest_r2_key.is_not(None),
                db.releases.c.state.in_(("published", "yanked", "blocked")),
            )
        ).first()
        if row is None:
            return None
        if _column(row, "state") == "blocked":
            raise RegistryBlockedError("Module Federation Distribution is operator-blocked")
        manifest_key = _column(row, "manifest_r2_key")
        prefix = manifest_key.removesuffix("mf-manifest.json")
        if relative_path not in json.loads(_column(row, "asset_paths_json")):
            return None
        return PublicObject(
            r2_key=prefix + relative_path,
            media_type=media_type,
            etag=_column(row, "internal_snapshot_hash"),
        )
