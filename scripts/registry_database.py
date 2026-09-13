"""Delivery-only provisioning of the login created by the permission migration."""

from urllib.parse import quote, urlsplit

import psycopg
from psycopg import sql


def configure_runtime_login(owner_url: str, password: str) -> str:
    # Neon rejects libpq's pre-hashed password changes. Use psycopg's literal
    # quoting over the owner TLS connection; never put this command in logs.
    with psycopg.connect(owner_url, autocommit=True, connect_timeout=30) as connection:
        connection.execute(
            sql.SQL("ALTER ROLE registry_app LOGIN PASSWORD {}").format(sql.Literal(password))
        )
    parsed = urlsplit(owner_url)
    authority = parsed.netloc.rsplit("@", 1)[-1]
    return parsed._replace(netloc=f"registry_app:{quote(password, safe='')}@{authority}").geturl()
