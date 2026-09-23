from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from semantic_version import Version

from ..contracts.models import (
    ExtensionRecord,
    ExtensionSummary,
    ReleaseDocumentation,
    ReleaseRecord,
)

ROOT = Path(__file__).parent
TEMPLATES = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    autoescape=select_autoescape(["html"]),
)
STYLES = (ROOT / "static" / "registry.css").read_text()
SCRIPT = (ROOT / "static" / "registry.js").read_text()
DEFAULT_CLIENT_WEB_ORIGIN = "https://app.inkcre.dev"


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
    query: str = "",
    namespace: str = "",
    client_origin: str = DEFAULT_CLIENT_WEB_ORIGIN,
) -> str:
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
        extensions=filtered,
        total=len(extensions),
        publishers=publishers,
        query=query,
        namespace=namespace,
        client_origin=client_origin,
    )


def select_release(extension: ExtensionRecord, version: str | None = None) -> ReleaseRecord | None:
    releases = sorted(extension.releases, key=lambda item: Version(item.version), reverse=True)
    if not releases:
        return None
    release: ReleaseRecord | None = next(
        (item for item in releases if item.version == version), None
    )
    if version is not None and release is None:
        return None
    if release is None:
        release = next(
            (item for item in releases if not Version(item.version).prerelease), releases[0]
        )
    return release


def extension_detail_html(
    extension: ExtensionRecord,
    version: str | None = None,
    documentation: ReleaseDocumentation | None = None,
    *,
    client_origin: str = DEFAULT_CLIENT_WEB_ORIGIN,
) -> str | None:
    releases = sorted(extension.releases, key=lambda item: Version(item.version), reverse=True)
    release = select_release(extension, version)
    if release is None:
        return None
    install_query = urlencode({"install": extension.name, "version": release.version})
    return page(
        "detail.html",
        title=extension.nickname,
        active="catalog",
        extension=extension,
        release=release,
        releases=releases,
        publisher=extension.name.split("/")[0],
        documentation=documentation,
        client_origin=client_origin,
        client_host=urlparse(client_origin).netloc,
        install_url=f"{client_origin}/extensions?{install_query}",
    )
