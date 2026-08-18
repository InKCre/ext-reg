from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .contracts import (
    ModuleFederationDistribution,
    PythonDistribution,
    PythonEntryPoint,
    ReleaseRecord,
    normalize_project_name,
)
from .module_federation import inspect_module_federation_snapshot
from .python_distribution import inspect_wheel, sha256_hex
from .simple import PythonFileRecord, project_file_url, project_html, root_html


class PreviewBuildError(ValueError):
    """One explicit preview input cannot produce a truthful static Registry."""


class _InventoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PythonPreviewDistribution(_InventoryModel):
    kind: Literal["python"]
    producer: str = Field(min_length=1)
    artifact: str = Field(min_length=1)


class ModuleFederationPreviewDistribution(_InventoryModel):
    kind: Literal["module_federation"]
    producer: str = Field(min_length=1)
    artifact: str = Field(min_length=1)


PreviewDistribution = Annotated[
    PythonPreviewDistribution | ModuleFederationPreviewDistribution,
    Field(discriminator="kind"),
]


class PreviewInventory(_InventoryModel):
    schema_version: Literal[1]
    distributions: tuple[PreviewDistribution, ...] = Field(min_length=1)


class PreviewBuildResult(_InventoryModel):
    extension_count: int
    release_count: int
    distribution_count: int
    output: str


class _ReleaseMaterial:
    def __init__(self, *, name: str, nickname: str, version: str) -> None:
        self.name = name
        self.nickname = nickname
        self.version = version
        self.python: PythonDistribution | None = None
        self.module_federation: ModuleFederationDistribution | None = None

    def record(self) -> ReleaseRecord:
        return ReleaseRecord(
            name=self.name,
            nickname=self.nickname,
            version=self.version,
            state="published",
            python=self.python,
            module_federation=self.module_federation,
        )


def _canonical_origin(value: str) -> str:
    parts = urlsplit(value.strip())
    if (
        parts.scheme not in {"http", "https"}
        or not parts.netloc
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise PreviewBuildError("public origin must be one HTTP(S) origin")
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _input_path(inventory_path: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = inventory_path.parent / candidate
    return candidate.resolve()


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreviewBuildError(f"cannot read JSON producer metadata: {path}") from error
    if not isinstance(value, dict):
        raise PreviewBuildError(f"producer metadata must be one JSON object: {path}")
    return value


def _read_toml(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise PreviewBuildError(f"cannot read TOML producer metadata: {path}") from error


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PreviewBuildError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreviewBuildError(f"{label} must be a non-empty string")
    return value


def _release(
    releases: dict[tuple[str, str], _ReleaseMaterial],
    *,
    name: str,
    nickname: str,
    version: str,
) -> _ReleaseMaterial:
    key = (name, version)
    existing = releases.get(key)
    if existing is None:
        existing = _ReleaseMaterial(name=name, nickname=nickname, version=version)
        releases[key] = existing
    elif existing.nickname != nickname:
        raise PreviewBuildError(f"conflicting nickname for {name}@{version}")
    return existing


def _snapshot_archive(directory: Path) -> bytes:
    if not directory.is_dir():
        raise PreviewBuildError(f"Module Federation artifact is not a directory: {directory}")
    with tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024) as buffer:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            files = sorted(path for path in directory.rglob("*") if path.is_file())
            if not files:
                raise PreviewBuildError("Module Federation artifact directory is empty")
            for path in files:
                if path.is_symlink():
                    raise PreviewBuildError("Module Federation artifact contains a symbolic link")
                relative = path.relative_to(directory).as_posix()
                if PurePosixPath(relative).as_posix() != relative:
                    raise PreviewBuildError("Module Federation artifact path is not canonical")
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        buffer.seek(0)
        return buffer.read()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _release_bytes(record: ReleaseRecord) -> bytes:
    value = record.model_dump(mode="json", exclude_none=True)
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _build_module_federation(
    item: ModuleFederationPreviewDistribution,
    *,
    inventory_path: Path,
    origin: str,
    output: Path,
    releases: dict[tuple[str, str], _ReleaseMaterial],
) -> None:
    producer = _read_json(_input_path(inventory_path, item.producer))
    inkcre = _object(producer.get("inkcre"), "package.json inkcre")
    association = _object(inkcre.get("module_federation"), "inkcre.module_federation")
    name = _string(inkcre.get("name"), "inkcre.name")
    nickname = _string(inkcre.get("nickname"), "inkcre.nickname")
    version = _string(producer.get("version"), "package.json version")
    host_sdk = _string(association.get("host_sdk"), "module_federation.host_sdk")
    if host_sdk != "@inkcre/core":
        raise PreviewBuildError("module_federation.host_sdk must be @inkcre/core")
    host_sdk_version = _string(
        association.get("host_sdk_version"), "module_federation.host_sdk_version"
    )
    prefix = f"/extensions/{name}/{version}/module-federation/"
    snapshot = inspect_module_federation_snapshot(
        _snapshot_archive(_input_path(inventory_path, item.artifact)),
        public_prefix=origin + prefix,
    )
    material = _release(releases, name=name, nickname=nickname, version=version)
    distribution = ModuleFederationDistribution(
        manifest_url=prefix + "mf-manifest.json",
        host_sdk=host_sdk,
        host_sdk_version=host_sdk_version,
    )
    if material.module_federation is not None:
        raise PreviewBuildError(f"duplicate Module Federation Distribution for {name}@{version}")
    material.module_federation = distribution
    for relative, content in sorted(snapshot.files.items()):
        _write(output / prefix.lstrip("/") / relative, content)


def _python_entry_point(project: dict[str, object]) -> PythonEntryPoint:
    entry_points = _object(project.get("entry-points"), "project.entry-points")
    group = _object(
        entry_points.get("inkcre.core.extensions"),
        'project.entry-points."inkcre.core.extensions"',
    )
    if len(group) != 1:
        raise PreviewBuildError("Python producer must declare exactly one Core entry point")
    name, object_reference = next(iter(group.items()))
    return PythonEntryPoint(
        group="inkcre.core.extensions",
        name=name,
        object=_string(object_reference, "Core entry-point object"),
    )


def _build_python(
    item: PythonPreviewDistribution,
    *,
    inventory_path: Path,
    output: Path,
    releases: dict[tuple[str, str], _ReleaseMaterial],
    files_by_project: dict[str, list[PythonFileRecord]],
    python_owners: dict[tuple[str, str], tuple[str, str]],
) -> None:
    producer = _read_toml(_input_path(inventory_path, item.producer))
    project = _object(producer.get("project"), "pyproject project")
    tool = _object(producer.get("tool"), "pyproject tool")
    association = _object(tool.get("inkcre-extension"), "tool.inkcre-extension")
    name = _string(association.get("name"), "tool.inkcre-extension.name")
    nickname = _string(association.get("nickname"), "tool.inkcre-extension.nickname")
    version = _string(project.get("version"), "project.version")
    project_name = _string(project.get("name"), "project.name")
    host_sdk = _string(association.get("host-sdk"), "tool.inkcre-extension.host-sdk")
    if host_sdk != "core-py":
        raise PreviewBuildError("tool.inkcre-extension.host-sdk must be core-py")
    host_sdk_version = _string(
        association.get("host-sdk-version"), "tool.inkcre-extension.host-sdk-version"
    )
    entry_point = _python_entry_point(project)
    wheel = _input_path(inventory_path, item.artifact)
    try:
        content = wheel.read_bytes()
    except OSError as error:
        raise PreviewBuildError(f"cannot read Python wheel: {wheel}") from error
    inspected = inspect_wheel(
        wheel.name,
        content,
        expected_project=project_name,
        expected_release_version=version,
        expected_entry_point=entry_point,
    )
    normalized_project = normalize_project_name(project_name)
    project_key = (normalized_project, inspected.project_version)
    release_key = (name, version)
    owner = python_owners.setdefault(project_key, release_key)
    if owner != release_key:
        raise PreviewBuildError(
            f"Python Project/version {normalized_project}=={inspected.project_version} "
            "belongs to multiple Extension Releases"
        )
    material = _release(releases, name=name, nickname=nickname, version=version)
    distribution = PythonDistribution(
        project=normalized_project,
        simple_url=f"/simple/{normalized_project}/",
        host_sdk=host_sdk,
        host_sdk_version=host_sdk_version,
        entry_point=entry_point,
    )
    if material.python is not None and material.python != distribution:
        raise PreviewBuildError(f"conflicting Python association for {name}@{version}")
    material.python = distribution
    metadata_digest = sha256_hex(inspected.metadata)
    record = PythonFileRecord(
        normalized_project=normalized_project,
        project_version=inspected.project_version,
        filename=wheel.name,
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        filetype="bdist_wheel",
        requires_python=inspected.requires_python,
        core_metadata_sha256=metadata_digest,
        r2_key="",
        metadata_r2_key="",
        uploaded_at="1970-01-01 00:00:00",
    )
    project_files = files_by_project.setdefault(normalized_project, [])
    if any(existing.filename == wheel.name for existing in project_files):
        raise PreviewBuildError(f"duplicate Python wheel filename: {wheel.name}")
    project_files.append(record)
    file_path = output / project_file_url(record).lstrip("/")
    _write(file_path, content)
    _write(Path(str(file_path) + ".metadata"), inspected.metadata)


def _headers() -> bytes:
    return (
        b"/v1/extensions/*\n"
        b"  Access-Control-Allow-Origin: *\n"
        b"  Cache-Control: no-store\n"
        b"  Content-Type: application/json; charset=utf-8\n"
        b"/simple/*\n"
        b"  Access-Control-Allow-Origin: *\n"
        b"  Cache-Control: no-store\n"
        b"  Content-Type: application/vnd.pypi.simple.v1+html; charset=utf-8\n"
        b"/packages/*\n"
        b"  Access-Control-Allow-Origin: *\n"
        b"  Cache-Control: public, max-age=31536000, immutable\n"
        b"/extensions/*\n"
        b"  Access-Control-Allow-Origin: *\n"
        b"  Cache-Control: no-store\n"
    )


def build_preview_registry(
    inventory_path: Path,
    public_origin: str,
    output_path: Path,
) -> PreviewBuildResult:
    """Build one deterministic, read-only native Registry projection."""

    inventory_path = inventory_path.resolve()
    inventory = PreviewInventory.model_validate_json(inventory_path.read_text(encoding="utf-8"))
    origin = _canonical_origin(public_origin)
    output_path = output_path.resolve()
    if output_path.exists() and any(output_path.iterdir()):
        raise PreviewBuildError("output directory must not exist or must be empty")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".inkcre-preview-", dir=output_path.parent))
    releases: dict[tuple[str, str], _ReleaseMaterial] = {}
    files_by_project: dict[str, list[PythonFileRecord]] = {}
    python_owners: dict[tuple[str, str], tuple[str, str]] = {}
    try:
        for item in sorted(
            inventory.distributions,
            key=lambda value: (value.kind, value.producer, value.artifact),
        ):
            if isinstance(item, PythonPreviewDistribution):
                _build_python(
                    item,
                    inventory_path=inventory_path,
                    output=staging,
                    releases=releases,
                    files_by_project=files_by_project,
                    python_owners=python_owners,
                )
            else:
                _build_module_federation(
                    item,
                    inventory_path=inventory_path,
                    origin=origin,
                    output=staging,
                    releases=releases,
                )
        for (name, version), material in sorted(releases.items()):
            namespace, local_name = name.split("/", 1)
            _write(
                staging / "v1" / "extensions" / namespace / local_name / "releases" / version,
                _release_bytes(material.record()),
            )
        projects = sorted(files_by_project)
        if projects:
            _write(staging / "simple" / "index.html", root_html(projects).encode())
            for project in projects:
                records = sorted(files_by_project[project], key=lambda value: value.filename)
                _write(
                    staging / "simple" / project / "index.html",
                    project_html(records).encode(),
                )
        _write(staging / "_headers", _headers())
        if output_path.exists():
            output_path.rmdir()
        os.replace(staging, output_path)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return PreviewBuildResult(
        extension_count=len({name for name, _version in releases}),
        release_count=len(releases),
        distribution_count=len(inventory.distributions),
        output=str(output_path),
    )


PREVIEW_INVENTORY_ADAPTER = TypeAdapter(PreviewInventory)
