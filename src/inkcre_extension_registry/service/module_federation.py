from __future__ import annotations

import hashlib
import io
import json
import math
import mimetypes
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Never

MAX_ARCHIVE_FILES = 4096
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class ModuleFederationValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ModuleFederationSnapshot:
    snapshot_hash: str
    files: dict[str, bytes]
    media_types: dict[str, str]


def validate_relative_asset_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or "?" in value
        or "#" in value
        or "://" in value
        or "\x00" in value
    ):
        raise ModuleFederationValidationError("asset path must be a relative URL-safe path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ModuleFederationValidationError("asset path must be normalized and traversal-free")
    if path.as_posix() != value:
        raise ModuleFederationValidationError("asset path must use normalized POSIX spelling")
    return value


def _archive_files(content: bytes) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise ModuleFederationValidationError("snapshot must be a valid ZIP archive") from error
    files: dict[str, bytes] = {}
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ModuleFederationValidationError("snapshot contains too many archive members")
        expanded = 0
        seen: set[str] = set()
        for info in infos:
            name = info.filename.removesuffix("/") if info.is_dir() else info.filename
            if not name or "\\" in name or "\x00" in name:
                raise ModuleFederationValidationError("snapshot contains an unsafe archive path")
            validate_relative_asset_path(name)
            if name in seen:
                raise ModuleFederationValidationError("snapshot contains a duplicated archive path")
            seen.add(name)
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise ModuleFederationValidationError("snapshot contains a symbolic link")
            if info.flag_bits & 0x1:
                raise ModuleFederationValidationError("encrypted snapshot members are unsupported")
            if info.is_dir():
                continue
            if info.file_size > MAX_MEMBER_BYTES:
                raise ModuleFederationValidationError("snapshot member exceeds the expansion limit")
            expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise ModuleFederationValidationError("snapshot exceeds the total expansion limit")
            if (
                info.file_size > 1024 * 1024
                and info.compress_size > 0
                and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise ModuleFederationValidationError(
                    "snapshot member has an unsafe compression ratio"
                )
            try:
                files[name] = archive.read(info)
            except (RuntimeError, zipfile.BadZipFile) as error:
                raise ModuleFederationValidationError(
                    "snapshot member cannot be read safely"
                ) from error
    return files


def _remote_entry_path(metadata: dict[str, Any]) -> str:
    remote_entry = metadata.get("remoteEntry")
    if not isinstance(remote_entry, dict):
        raise ModuleFederationValidationError("metaData.remoteEntry must be an object")
    name = remote_entry.get("name")
    path = remote_entry.get("path", "")
    if not isinstance(name, str) or not isinstance(path, str):
        raise ModuleFederationValidationError("Remote entry path and name must be strings")
    combined = f"{path.rstrip('/')}/{name}" if path else name
    return validate_relative_asset_path(combined.removeprefix("./"))


def _asset_references(items: Any, collection_name: str) -> set[str]:
    if not isinstance(items, list):
        raise ModuleFederationValidationError(f"{collection_name} must be an array")
    references: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ModuleFederationValidationError(f"{collection_name} entries must be objects")
        assets = item.get("assets", {})
        if not isinstance(assets, dict):
            raise ModuleFederationValidationError("manifest assets must be objects")
        for kind in ("js", "css"):
            groups = assets.get(kind, {})
            if not isinstance(groups, dict):
                raise ModuleFederationValidationError(f"manifest {kind} assets must be objects")
            for timing in ("sync", "async"):
                paths = groups.get(timing, [])
                if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
                    raise ModuleFederationValidationError(
                        f"manifest {kind}.{timing} assets must be string arrays"
                    )
                references.update(validate_relative_asset_path(path) for path in paths)
    return references


def _snapshot_hash(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for relative_path, content in sorted(files.items()):
        encoded_path = relative_path.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _reject_non_finite_json(value: str) -> Never:
    raise ModuleFederationValidationError(
        f"mf-manifest.json must not contain non-finite number {value}"
    )


def _parse_finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        _reject_non_finite_json(value)
    return parsed


def inspect_module_federation_snapshot(
    content: bytes, *, public_prefix: str
) -> ModuleFederationSnapshot:
    files = _archive_files(content)
    raw_manifest = files.get("mf-manifest.json")
    if raw_manifest is None:
        raise ModuleFederationValidationError("snapshot must contain root mf-manifest.json")
    try:
        manifest = json.loads(
            raw_manifest,
            parse_constant=_reject_non_finite_json,
            parse_float=_parse_finite_json_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ModuleFederationValidationError(
            "mf-manifest.json must be valid UTF-8 JSON"
        ) from error
    if not isinstance(manifest, dict):
        raise ModuleFederationValidationError("mf-manifest.json must contain an object")
    metadata = manifest.get("metaData")
    if not isinstance(metadata, dict):
        raise ModuleFederationValidationError("mf-manifest.json requires metaData")
    if metadata.get("publicPath") != "./":
        raise ModuleFederationValidationError("metaData.publicPath must be './'")

    references = {_remote_entry_path(metadata)}
    references.update(_asset_references(manifest.get("shared", []), "shared"))
    references.update(_asset_references(manifest.get("exposes", []), "exposes"))
    missing = sorted(path for path in references if path not in files)
    if missing:
        raise ModuleFederationValidationError(
            "manifest references missing assets: " + ", ".join(missing[:10])
        )

    if not public_prefix.startswith(("https://", "http://")) or not public_prefix.endswith("/"):
        raise ModuleFederationValidationError("publicPath must be an absolute URL prefix")
    metadata["publicPath"] = public_prefix
    files["mf-manifest.json"] = json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    snapshot_hash = _snapshot_hash(files)
    media_types = {
        relative_path: (
            "application/json"
            if relative_path == "mf-manifest.json"
            else mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        )
        for relative_path in files
    }
    return ModuleFederationSnapshot(
        snapshot_hash=snapshot_hash,
        files=files,
        media_types=media_types,
    )
