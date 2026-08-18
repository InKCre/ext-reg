from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from inkcre_extension_toolkit.simple import PythonFileRecord

from ..contracts.models import (
    ExtensionRecord,
    ExtensionSummary,
    ModuleFederationAssociationInput,
    ModuleFederationDistribution,
    PrepareReleaseRequest,
    PythonAssociationInput,
    PythonDistribution,
    PythonEntryPoint,
    ReleaseRecord,
    normalize_project_name,
    python_project_version,
)


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

    async def authenticate(self, token_hash: str) -> str | None:
        row = (
            await self.db.prepare(
                "SELECT c.namespace FROM credentials c JOIN namespaces n "
                "ON n.name = c.namespace WHERE c.token_hash = ?1 "
                "AND c.disabled = 0 AND n.status = 'active'"
            )
            .bind(token_hash)
            .first()
        )
        return _column(row, "namespace")

    async def _extension_row(self, extension_name: str) -> Any:
        return (
            await self.db.prepare(
                "SELECT name, namespace, nickname FROM extensions WHERE name = ?1"
            )
            .bind(extension_name)
            .first()
        )

    async def _release_row(self, extension_name: str, version: str) -> Any:
        return (
            await self.db.prepare(
                "SELECT e.nickname, r.extension_name, r.version, r.state, r.yank_reason, "
                "r.created_at "
                "FROM releases r JOIN extensions e ON e.name = r.extension_name "
                "WHERE r.extension_name = ?1 AND r.version = ?2"
            )
            .bind(extension_name, version)
            .first()
        )

    async def _python_row(self, extension_name: str, version: str) -> Any:
        return (
            await self.db.prepare(
                "SELECT * FROM python_distributions WHERE extension_name = ?1 "
                "AND release_version = ?2"
            )
            .bind(extension_name, version)
            .first()
        )

    async def _module_federation_row(self, extension_name: str, version: str) -> Any:
        return (
            await self.db.prepare(
                "SELECT * FROM module_federation_distributions WHERE extension_name = ?1 "
                "AND release_version = ?2"
            )
            .bind(extension_name, version)
            .first()
        )

    async def _python_project_owner(self, normalized_project: str, version: str) -> str | None:
        row = (
            await self.db.prepare(
                "SELECT extension_name FROM python_distributions "
                "WHERE normalized_project = ?1 AND project_version = ?2"
            )
            .bind(normalized_project, version)
            .first()
        )
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
            self.db.prepare(
                "INSERT INTO extensions(name, namespace, nickname) VALUES (?1, ?2, ?3) "
                "ON CONFLICT(name) DO NOTHING"
            ).bind(extension_name, namespace, request.nickname),
            self.db.prepare(
                "INSERT INTO releases(extension_name, version) VALUES (?1, ?2) "
                "ON CONFLICT(extension_name, version) DO NOTHING"
            ).bind(extension_name, request.version),
        ]
        if adds_python and request.python is not None:
            statements.append(
                self.db.prepare(
                    "INSERT INTO python_distributions(extension_name, release_version, "
                    "normalized_project, project_version, host_sdk, host_sdk_range, "
                    "entry_group, entry_name, entry_object, source_repository, "
                    "source_revision, build_id) "
                    "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)"
                ).bind(
                    extension_name,
                    request.version,
                    normalize_project_name(request.python.project),
                    python_project_version(request.version),
                    request.python.host_sdk,
                    request.python.host_sdk_version,
                    request.python.entry_point.group,
                    request.python.entry_point.name,
                    request.python.entry_point.object,
                    request.python.source_repository,
                    request.python.source_revision,
                    request.python.build_id,
                )
            )
        if adds_mf and request.module_federation is not None:
            statements.append(
                self.db.prepare(
                    "INSERT INTO module_federation_distributions(extension_name, "
                    "release_version, host_sdk, host_sdk_range, source_repository, "
                    "source_revision, build_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)"
                ).bind(
                    extension_name,
                    request.version,
                    request.module_federation.host_sdk,
                    request.module_federation.host_sdk_version,
                    request.module_federation.source_repository,
                    request.module_federation.source_revision,
                    request.module_federation.build_id,
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
            file_row = (
                await self.db.prepare(
                    "SELECT 1 AS ready FROM python_files WHERE normalized_project = ?1 "
                    "AND project_version = ?2 LIMIT 1"
                )
                .bind(
                    _column(python_row, "normalized_project"),
                    _column(python_row, "project_version"),
                )
                .first()
            )
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

    async def list_extensions(self) -> list[ExtensionSummary]:
        result = await self.db.prepare(
            "SELECT e.name, e.nickname FROM extensions e "
            "WHERE EXISTS (SELECT 1 FROM releases r WHERE r.extension_name = e.name "
            "AND r.state = 'published') ORDER BY e.name"
        ).all()
        return [
            ExtensionSummary(name=_column(row, "name"), nickname=_column(row, "nickname"))
            for row in _results(result)
        ]

    async def get_extension(self, extension_name: str) -> ExtensionRecord | None:
        extension = await self._extension_row(extension_name)
        if extension is None:
            return None
        versions = (
            await self.db.prepare(
                "SELECT version FROM releases WHERE extension_name = ?1 AND state = 'published' "
                "ORDER BY created_at DESC, version DESC"
            )
            .bind(extension_name)
            .all()
        )
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
            result = (
                await self.db.prepare(
                    "UPDATE releases SET state = 'published', yank_reason = NULL, "
                    "published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                    "WHERE extension_name = ?1 AND version = ?2 AND state = 'preparing' "
                    "AND (EXISTS (SELECT 1 FROM python_distributions pd JOIN python_files pf "
                    "ON pf.normalized_project = pd.normalized_project "
                    "AND pf.project_version = pd.project_version "
                    "WHERE pd.extension_name = ?1 AND pd.release_version = ?2) "
                    "OR EXISTS (SELECT 1 FROM module_federation_distributions mf "
                    "WHERE mf.extension_name = ?1 AND mf.release_version = ?2 "
                    "AND mf.manifest_r2_key IS NOT NULL))"
                )
                .bind(extension_name, version)
                .run()
            )
            if int(_column(_column(result, "meta"), "changes", 0)) != 1:
                raise RegistryStateError(
                    "Release requires at least one validated native Distribution"
                )
        published = await self.get_release(extension_name, version)
        if published is None:
            raise RuntimeError("published Release is not readable")
        return published

    async def _release_objects_available(self, extension_name: str, version: str) -> bool:
        python_result = (
            await self.db.prepare(
                "SELECT pf.r2_key, pf.metadata_r2_key, pf.size FROM python_files pf "
                "JOIN python_distributions pd "
                "ON pd.normalized_project = pf.normalized_project "
                "AND pd.project_version = pf.project_version "
                "WHERE pd.extension_name = ?1 AND pd.release_version = ?2"
            )
            .bind(extension_name, version)
            .all()
        )
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
            await (
                self.db.prepare(
                    "UPDATE releases SET state = 'yanked', yank_reason = ?3, "
                    "updated_at = CURRENT_TIMESTAMP WHERE extension_name = ?1 "
                    "AND version = ?2 AND state = 'published'"
                )
                .bind(extension_name, version, reason)
                .run()
            )
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
            await (
                self.db.prepare(
                    "UPDATE releases SET state = 'published', yank_reason = NULL, "
                    "updated_at = CURRENT_TIMESTAMP WHERE extension_name = ?1 "
                    "AND version = ?2 AND state = 'yanked'"
                )
                .bind(extension_name, version)
                .run()
            )
        elif state != "published":
            raise RegistryStateError(f"cannot unyank a {state} Release")
        published = await self.get_release(extension_name, version)
        if published is None:
            raise RuntimeError("unyanked Release is not readable")
        return published

    async def prepared_python_distribution(
        self, namespace: str, normalized_project: str, project_version: str
    ) -> PreparedPythonDistribution | None:
        row = (
            await self.db.prepare(
                "SELECT pd.*, r.state FROM python_distributions pd "
                "JOIN releases r ON r.extension_name = pd.extension_name "
                "AND r.version = pd.release_version "
                "JOIN extensions e ON e.name = pd.extension_name "
                "WHERE e.namespace = ?1 AND pd.normalized_project = ?2 "
                "AND pd.project_version = ?3"
            )
            .bind(namespace, normalized_project, project_version)
            .first()
        )
        return _prepared_python(row) if row is not None else None

    async def prepared_python_distributions(
        self, namespace: str, normalized_project: str
    ) -> list[PreparedPythonDistribution]:
        result = (
            await self.db.prepare(
                "SELECT pd.*, r.state FROM python_distributions pd "
                "JOIN releases r ON r.extension_name = pd.extension_name "
                "AND r.version = pd.release_version "
                "JOIN extensions e ON e.name = pd.extension_name "
                "WHERE e.namespace = ?1 AND pd.normalized_project = ?2"
            )
            .bind(namespace, normalized_project)
            .all()
        )
        return [_prepared_python(row) for row in _results(result)]

    async def _python_file_row(
        self, normalized_project: str, project_version: str, filename: str
    ) -> Any:
        return (
            await self.db.prepare(
                "SELECT * FROM python_files WHERE normalized_project = ?1 "
                "AND project_version = ?2 AND filename = ?3"
            )
            .bind(normalized_project, project_version, filename)
            .first()
        )

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
            await (
                self.db.prepare(
                    "INSERT INTO python_files(normalized_project, project_version, filename, "
                    "sha256, size, filetype, requires_python, core_metadata_sha256, r2_key, "
                    "metadata_r2_key) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)"
                )
                .bind(
                    distribution.normalized_project,
                    distribution.project_version,
                    filename,
                    sha256,
                    len(content),
                    filetype,
                    requires_python,
                    metadata_sha256,
                    r2_key,
                    metadata_r2_key,
                )
                .run()
            )
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
        result = await self.db.prepare(
            "SELECT DISTINCT pd.normalized_project FROM python_distributions pd "
            "JOIN releases r ON r.extension_name = pd.extension_name "
            "AND r.version = pd.release_version JOIN python_files pf "
            "ON pf.normalized_project = pd.normalized_project "
            "AND pf.project_version = pd.project_version "
            "WHERE r.state IN ('published', 'yanked') ORDER BY pd.normalized_project"
        ).all()
        return [_column(row, "normalized_project") for row in _results(result)]

    async def simple_files(self, normalized_project: str) -> list[PythonFileRecord]:
        result = (
            await self.db.prepare(
                "SELECT pf.*, CASE WHEN r.state = 'yanked' THEN r.yank_reason ELSE NULL END "
                "AS yank_reason FROM python_files pf JOIN python_distributions pd "
                "ON pd.normalized_project = pf.normalized_project "
                "AND pd.project_version = pf.project_version JOIN releases r "
                "ON r.extension_name = pd.extension_name AND r.version = pd.release_version "
                "WHERE pf.normalized_project = ?1 AND r.state IN ('published', 'yanked') "
                "ORDER BY pf.filename"
            )
            .bind(normalized_project)
            .all()
        )
        return [_python_file(row) for row in _results(result)]

    async def python_public_file(
        self,
        normalized_project: str,
        project_version: str,
        filename: str,
        *,
        metadata: bool = False,
    ) -> PublicObject | None:
        row = (
            await self.db.prepare(
                "SELECT pf.*, r.state FROM python_files pf JOIN python_distributions pd "
                "ON pd.normalized_project = pf.normalized_project "
                "AND pd.project_version = pf.project_version JOIN releases r "
                "ON r.extension_name = pd.extension_name AND r.version = pd.release_version "
                "WHERE pf.normalized_project = ?1 AND pf.project_version = ?2 "
                "AND pf.filename = ?3 AND r.state IN ('published', 'yanked', 'blocked')"
            )
            .bind(normalized_project, project_version, filename)
            .first()
        )
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
        result = (
            await self.db.prepare(
                "UPDATE module_federation_distributions SET manifest_r2_key = ?3, "
                "asset_paths_json = ?4, internal_snapshot_hash = ?5, "
                "uploaded_at = CURRENT_TIMESTAMP "
                "WHERE extension_name = ?1 AND release_version = ?2 "
                "AND manifest_r2_key IS NULL"
            )
            .bind(
                extension_name,
                version,
                manifest_key,
                json.dumps(sorted(files), separators=(",", ":")),
                snapshot_hash,
            )
            .run()
        )
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
        row = (
            await self.db.prepare(
                "SELECT mf.manifest_r2_key, mf.asset_paths_json, "
                "mf.internal_snapshot_hash, r.state "
                "FROM module_federation_distributions mf JOIN releases r "
                "ON r.extension_name = mf.extension_name AND r.version = mf.release_version "
                "WHERE mf.extension_name = ?1 AND mf.release_version = ?2 "
                "AND mf.manifest_r2_key IS NOT NULL "
                "AND r.state IN ('published', 'yanked', 'blocked')"
            )
            .bind(extension_name, version)
            .first()
        )
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
