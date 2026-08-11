from __future__ import annotations

import html
from urllib.parse import quote

from .repository import PythonFileRecord

SIMPLE_HTML = "application/vnd.pypi.simple.v1+html"
SIMPLE_JSON = "application/vnd.pypi.simple.v1+json"


def negotiate_simple(accept: str | None) -> str | None:
    if not accept:
        return SIMPLE_HTML
    candidates: list[tuple[float, int, str]] = []
    for position, raw_item in enumerate(accept.split(",")):
        parts = [part.strip() for part in raw_item.split(";")]
        media_type = parts[0].lower()
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        if quality <= 0:
            continue
        if media_type in {SIMPLE_JSON, "application/json"}:
            candidates.append((quality, -position, SIMPLE_JSON))
        elif media_type in {SIMPLE_HTML, "text/html", "*/*"}:
            candidates.append((quality, -position, SIMPLE_HTML))
    if not candidates:
        return None
    return max(candidates)[2]


def project_file_url(file: PythonFileRecord) -> str:
    return (
        f"/packages/{quote(file.normalized_project, safe='-')}/"
        f"{quote(file.project_version, safe='.-')}/{quote(file.filename, safe='.-_')}"
    )


def root_json(projects: list[str]) -> dict[str, object]:
    return {
        "meta": {"api-version": "1.1"},
        "projects": [{"name": project} for project in projects],
    }


def project_json(project: str, files: list[PythonFileRecord]) -> dict[str, object]:
    values: list[dict[str, object]] = []
    for file in files:
        item: dict[str, object] = {
            "filename": file.filename,
            "url": project_file_url(file),
            "hashes": {"sha256": file.sha256},
            "requires-python": file.requires_python,
            "core-metadata": {"sha256": file.core_metadata_sha256},
            "size": file.size,
            "upload-time": file.uploaded_at.replace(" ", "T") + "Z",
            "yanked": file.yank_reason if file.yank_reason is not None else False,
        }
        values.append(item)
    return {"meta": {"api-version": "1.1"}, "name": project, "files": values}


def root_html(projects: list[str]) -> str:
    links = "\n".join(
        f'<a href="/simple/{quote(project, safe="-")}/">{html.escape(project)}</a><br/>'
        for project in projects
    )
    return (
        "<!DOCTYPE html>\n<html><head>"
        '<meta name="pypi:repository-version" content="1.1">'
        f"</head><body>\n{links}\n</body></html>\n"
    )


def project_html(files: list[PythonFileRecord]) -> str:
    links: list[str] = []
    for file in files:
        attributes = [
            f'href="{html.escape(project_file_url(file))}#sha256={file.sha256}"',
            f'data-core-metadata="sha256={file.core_metadata_sha256}"',
        ]
        if file.requires_python is not None:
            attributes.append(f'data-requires-python="{html.escape(file.requires_python)}"')
        if file.yank_reason is not None:
            attributes.append(f'data-yanked="{html.escape(file.yank_reason)}"')
        links.append(f"<a {' '.join(attributes)}>{html.escape(file.filename)}</a><br/>")
    return (
        "<!DOCTYPE html>\n<html><head>"
        '<meta name="pypi:repository-version" content="1.1">'
        f"</head><body>\n{'\n'.join(links)}\n</body></html>\n"
    )
