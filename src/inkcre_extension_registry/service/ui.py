from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from semantic_version import Version

from ..contracts.models import ExtensionRecord, ExtensionSummary, ReleaseRecord

ROOT = Path(__file__).parent
TEMPLATES = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    autoescape=select_autoescape(["html"]),
)
STYLES = (ROOT / "static" / "registry.css").read_text()
SCRIPT = (ROOT / "static" / "registry.js").read_text()


def _canonical_api_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("api_origin must be a canonical absolute HTTPS origin")
    return value


def page(template: str, **context: object) -> str:
    return TEMPLATES.get_template(template).render(styles=STYLES, **context)


def html_response(document: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        document,
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


def extension_catalog_html(
    extensions: Sequence[ExtensionSummary],
    *,
    api_origin: str | None = None,
    noindex: bool = False,
    query: str = "",
    namespace: str = "",
) -> str:
    origin = _canonical_api_origin(api_origin) if api_origin is not None else ""
    publishers = sorted({extension.name.split("/")[0] for extension in extensions})
    filtered = [
        extension
        for extension in extensions
        if query.casefold() in f"{extension.name} {extension.nickname}".casefold()
        and (not namespace or extension.name.split("/")[0] == namespace)
    ]
    return page(
        "catalog.html",
        title="Extensions",
        active="catalog",
        origin=origin,
        noindex=noindex,
        preview=api_origin is not None,
        extensions=filtered,
        total=len(extensions),
        publishers=publishers,
        query=query,
        namespace=namespace,
    )


def extension_detail_html(extension: ExtensionRecord, version: str | None = None) -> str | None:
    releases = sorted(extension.releases, key=lambda item: Version(item.version), reverse=True)
    release: ReleaseRecord | None = next(
        (item for item in releases if item.version == version), None
    )
    if version is not None and release is None:
        return None
    if release is None:
        release = next(
            (item for item in releases if not Version(item.version).prerelease), releases[0]
        )
    return page(
        "detail.html",
        title=extension.nickname,
        active="catalog",
        extension=extension,
        release=release,
        releases=releases,
        publisher=extension.name.split("/")[0],
    )
