"""Static-site admission shared by authors and Registry; no SSG or MF semantics."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field

from .generated.documentation import DocumentationUpload
from .semantic import CanonicalExtensionName, ContractModel, StrictSemVer


class DocumentationCandidate(ContractModel):
    name: CanonicalExtensionName
    version: StrictSemVer
    scope: Literal["global", "python", "module-federation"]
    metadata: DocumentationUpload
    expected_etag: str | None = Field(default=None, pattern=r'^"[0-9a-f]{64}"$')


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_FILES = 4096
MEDIA_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".json": "application/json",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".pdf": "application/pdf",
    ".wasm": "application/wasm",
    ".webmanifest": "application/manifest+json",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ogg": "audio/ogg",
    ".map": "application/json",
}


def document_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or len(value.encode("utf-8")) > 768
        or path.is_absolute()
        or path.as_posix() != value
        or any(part.startswith(".") or part in {"_headers", "_redirects"} for part in path.parts)
        or any(character in value for character in "\\%?#:")
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(
            "documentation paths must be normalized, relative URL paths without hidden files"
        )
    return value


@dataclass(frozen=True)
class DocumentationBundle:
    files: dict[str, bytes]
    manifest: dict[str, dict]
    digest: str


def inspect_documentation(content: bytes, entry: str = "index.html") -> DocumentationBundle:
    document_path(entry)
    if not entry.endswith(".html"):
        raise ValueError("documentation entry must be an HTML file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("documentation ZIP exceeds 20 MiB")
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_FILES:
                raise ValueError("documentation ZIP exceeds 4096 members")
            expanded = 0
            seen: set[str] = set()
            for member in members:
                name = document_path(member.filename.removesuffix("/"))
                mode = member.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (
                    name in seen
                    or member.flag_bits & 1
                    or kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                ):
                    raise ValueError(
                        "documentation ZIP has a duplicate, encrypted, or special member"
                    )
                seen.add(name)
                if member.is_dir():
                    continue
                if kind == stat.S_IFDIR or PurePosixPath(name).suffix not in MEDIA_TYPES:
                    raise ValueError(f"unsupported static file type: {name}")
                expanded += member.file_size
                if member.file_size > MAX_UPLOAD_BYTES or expanded > MAX_EXPANDED_BYTES:
                    raise ValueError("documentation ZIP exceeds expanded size limits")
                if member.file_size > 1024 * 1024 and member.file_size > 200 * max(
                    member.compress_size, 1
                ):
                    raise ValueError("documentation ZIP has an unsafe compression ratio")
                files[name] = archive.read(member)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as error:
        raise ValueError("documentation must be a readable, unencrypted ZIP") from error
    if entry not in files:
        raise ValueError("documentation entry is absent from ZIP")
    # A file cannot also be a directory; otherwise exact and directory routes disagree.
    if any(str(parent) in files for name in files for parent in PurePosixPath(name).parents):
        raise ValueError("documentation ZIP contains a file/directory collision")
    manifest = {
        name: {
            "sha256": hashlib.sha256(value).hexdigest(),
            "size": len(value),
            "media_type": MEDIA_TYPES[PurePosixPath(name).suffix],
        }
        for name, value in sorted(files.items())
    }
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DocumentationBundle(files, manifest, digest)


def pack_documentation(directory: Path, entry: str = "index.html") -> bytes:
    """Pack output bytes, rejecting symlinks rather than following them outside the site."""
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("site must be a real directory")
    output = io.BytesIO()
    expanded = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        count = 0
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("site must not contain symlinks")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError("site must contain only regular files")
            count += 1
            expanded += path.stat().st_size
            if (
                count > MAX_FILES
                or expanded > MAX_EXPANDED_BYTES
                or path.stat().st_size > MAX_UPLOAD_BYTES
            ):
                raise ValueError("site exceeds documentation limits")
            name = document_path(path.relative_to(directory).as_posix())
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes())
    content = output.getvalue()
    inspect_documentation(content, entry)
    return content
