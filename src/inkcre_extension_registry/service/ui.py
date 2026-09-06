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
    query: str = "",
    namespace: str = "",
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
    )


def _detail_context(
    extension: ExtensionRecord, version: str | None = None
) -> dict[str, object] | None:
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
    return dict(
        extension=extension,
        release=release,
        releases=releases,
        publisher=extension.name.split("/")[0],
    )


def extension_detail_html(extension: ExtensionRecord, version: str | None = None) -> str | None:
    context = _detail_context(extension, version)
    if context is None:
        return None
    return page("detail.html", title=extension.nickname, active="catalog", **context)


def extension_preview_html(extensions: Sequence[ExtensionRecord], *, api_origin: str) -> str:
    """Render the catalog and sample release views within the bounded Pages document."""
    _canonical_api_origin(api_origin)
    details = []
    for extension in extensions:
        default = _detail_context(extension)
        if default is None:
            raise ValueError("preview extensions require a release")
        details.append({**default, "default": True})
        for release in extension.releases:
            details.append({**default, "release": release, "default": False})
    return page(
        "preview.html",
        title="Registry preview",
        active="catalog",
        preview=True,
        extensions=extensions,
        details=details,
        total=len(extensions),
    )
