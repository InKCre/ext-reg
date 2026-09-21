"""Environment configuration shared by the ASGI service and database tooling."""

from __future__ import annotations

import os
import re
import ssl
from dataclasses import dataclass, field
from urllib.parse import parse_qs, unquote, urlparse


def database_config(url: str) -> dict:
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not parsed.path[1:]
    ):
        raise ValueError("DATABASE_URL must address a PostgreSQL database")
    query = parse_qs(parsed.query)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    tls = query.get("sslmode", ["disable" if local else "verify-full"])[0]
    if tls not in {"disable", "require", "verify-ca", "verify-full"}:
        raise ValueError("Unsupported PostgreSQL sslmode")
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": parsed.hostname,
                    "port": parsed.port or 5432,
                    "user": unquote(parsed.username or ""),
                    "password": unquote(parsed.password or ""),
                    "database": unquote(parsed.path[1:]),
                    "ssl": False if tls == "disable" else ssl.create_default_context(),
                    "minsize": 1,
                    "maxsize": 5,
                    "timeout": 10,
                    "command_timeout": 30,
                    "application_name": "inkcre-extension-registry",
                },
            }
        },
        "apps": {
            "models": {
                "models": ["inkcre_extension_registry.service.database"],
                "default_connection": "default",
                "migrations": "inkcre_extension_registry.migrations",
            }
        },
        "use_tz": True,
        "timezone": "UTC",
    }


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    public_origin: str
    s3_endpoint_url: str
    s3_bucket: str
    documentation_origin_template: str | None = None

    def documentation_origin(self, snapshot_id: str) -> str:
        if self.documentation_origin_template is None:
            raise ValueError("documentation content origin is not configured")
        if not re.fullmatch(r"[0-9a-f]{32}", snapshot_id):
            raise ValueError("invalid documentation snapshot identity")
        return self.documentation_origin_template.replace("{snapshot}", snapshot_id)

    def documentation_snapshot(self, authority: str) -> str | None:
        if self.documentation_origin_template is None:
            return None
        template = urlparse(self.documentation_origin_template).netloc.lower()
        match = re.fullmatch(
            re.escape(template).replace(r"\{snapshot\}", "([0-9a-f]{32})"), authority.lower()
        )
        return match.group(1) if match else None

    @classmethod
    def from_env(cls) -> Settings:
        origin = os.environ["PUBLIC_ORIGIN"].rstrip("/")
        parsed = urlparse(origin)
        local_http = parsed.scheme == "http" and parsed.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }
        if (
            (parsed.scheme != "https" and not local_http)
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.params
        ):
            raise ValueError("PUBLIC_ORIGIN must be an absolute HTTPS origin")
        documentation_origin = os.environ.get("DOCUMENTATION_ORIGIN_TEMPLATE")
        if documentation_origin is not None:
            content = urlparse(documentation_origin)
            local_content = content.scheme == "http" and (content.hostname or "").endswith(
                ".localhost"
            )
            if (
                documentation_origin.count("{snapshot}") != 1
                or not (content.hostname or "").startswith("{snapshot}.")
                or (content.scheme != "https" and not local_content)
                or (local_content and not local_http)
                or content.username is not None
                or content.password is not None
                or content.path
                or content.query
                or content.fragment
                or content.params
                or "{" in documentation_origin.replace("{snapshot}", "")
                or "}" in documentation_origin.replace("{snapshot}", "")
            ):
                raise ValueError(
                    "DOCUMENTATION_ORIGIN_TEMPLATE must be a separate wildcard HTTPS origin "
                    "with a leading {snapshot} label"
                )
        return cls(
            database_url=os.environ["DATABASE_URL"],
            public_origin=origin,
            s3_endpoint_url=os.environ["S3_ENDPOINT_URL"],
            s3_bucket=os.environ["S3_BUCKET"],
            documentation_origin_template=documentation_origin,
        )
