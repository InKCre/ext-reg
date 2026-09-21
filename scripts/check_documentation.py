"""Documentation's public HTTP, storage atomicity, and lifecycle acceptance boundary."""

from __future__ import annotations

import asyncio
import io
import json
import os
import secrets
import stat
import zipfile
from unittest.mock import patch

import httpx
from inkcre_extension_toolkit.client import (
    DocumentationOutcomeUnknown,
    RegistryClient,
    RegistryHTTPError,
)
from inkcre_extension_toolkit.documentation import inspect_documentation
from inkcre_extension_toolkit.generated.documentation import DocumentationUpload
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from inkcre_extension_registry.service import database as db
from inkcre_extension_registry.service.settings import Settings


def check_content_sites() -> None:
    """Configuration must enforce the promised cookie-site isolation before serving HTML."""
    for management, content, accepted in (
        ("https://registry.example.com", "https://{snapshot}.docs.example.com", False),
        ("https://registry.example.co.uk", "https://{snapshot}.docs.example.co.uk", False),
        ("https://registry.example.com", "https://{snapshot}.exampleusercontent.net", True),
        ("https://registry.team.github.io", "https://{snapshot}.docs.team.github.io", False),
        ("https://registry.team.github.io", "https://{snapshot}.other.github.io", True),
        ("http://localhost", "http://{snapshot}.docs.localhost", True),
        ("https://registry.example.com", "http://{snapshot}.docs.localhost", False),
    ):
        with patch.dict(
            os.environ, PUBLIC_ORIGIN=management, DOCUMENTATION_ORIGIN_TEMPLATE=content
        ):
            try:
                Settings.from_env()
            except ValueError:
                assert not accepted, (management, content)
            else:
                assert accepted, (management, content)
    with patch.dict(
        os.environ,
        PUBLIC_ORIGIN="https://registry.example.com",
        DOCUMENTATION_ORIGIN_TEMPLATE="https://{snapshot}.EXAMPLEUSERCONTENT.NET",
    ):
        settings = Settings.from_env()
        identity = "a" * 32
        assert settings.documentation_snapshot(f"{identity}.exampleusercontent.net") == identity


def archive(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    return output.getvalue()


async def check_documentation(
    client: httpx.AsyncClient, token: str, other_token: str, artifacts
) -> None:
    check_content_sites()
    authorization = {"Authorization": f"Bearer {token}"}
    base = "/v1/extensions/check/documentation/releases/1.0.0"
    docs = base + "/documentation"
    entry_url = "/documentation/check/documentation/1.0.0/global/"
    private = docs.replace("/v1/", "/v1/publisher/", 1)

    async def request(method, path, expected=200, **kwargs):
        response = await client.request(method, path, **kwargs)
        assert response.status_code == expected, (
            method,
            path,
            response.status_code,
            response.text[:800],
        )
        return response

    await request(
        "POST",
        base.rsplit("/", 1)[0],
        headers=authorization,
        json={
            "nickname": "Documentation acceptance",
            "version": "1.0.0",
            "module_federation": {
                "source_repository": "https://example.invalid/repo",
                "source_revision": "revision",
                "host_sdk": "@inkcre/core",
                "host_sdk_version": "^1.0.0",
            },
        },
    )
    files = {
        "index.html": '<link rel="stylesheet" href="/assets/main.css"><a href="/guide">Guide</a>',
        "assets/main.css": "body { color: green; }",
        "guide/index.html": "Directory guide",
        "clean.html": "Clean URL",
        "search.json": '{"guide":"find me"}',
    }
    zipped = archive(files)

    def metadata(content=zipped):
        return {
            "snapshot_id": secrets.token_hex(16),
            "content_sha256": inspect_documentation(content).digest,
            "source_repository": "https://example.invalid/repo",
            "source_revision": "revision",
            "entry": "index.html",
            "build_id": "check",
            "expected_etag": None,
        }

    async def upload(payload, content=zipped, expected=200, headers=None, scope="global"):
        return await request(
            "POST",
            docs + "/" + scope,
            expected,
            headers={**authorization, **(headers or {})},
            data={"metadata": json.dumps(payload)},
            files={"content": ("docs.zip", content)},
        )

    first = metadata()
    await upload(first, expected=401, headers={"Authorization": ""})
    await upload(first, expected=403, headers={"Authorization": f"Bearer {other_token}"})
    await upload(
        {key: value for key, value in first.items() if key != "expected_etag"}, expected=400
    )
    await upload(first, expected=409, scope="python")
    first_response = await upload(first)
    assert "etag" not in first_response.headers
    first_record = first_response.json()
    assert (await upload(first)).json() == first_record
    assert (await request("GET", private, headers=authorization)).json()["sets"][0][
        "snapshot_id"
    ] == first["snapshot_id"]
    await request("GET", docs, 404)
    await request("GET", entry_url, 404)
    await request("GET", first_record["snapshot_url"], 404)
    await request("POST", base + "/publish", 409, headers=authorization)
    await request(
        "POST",
        base + "/module-federation",
        headers=authorization,
        files={
            "content": (
                "mf.zip",
                archive(
                    {
                        "mf-manifest.json": json.dumps(
                            {
                                "metaData": {
                                    "publicPath": "./",
                                    "remoteEntry": {"name": "remoteEntry.js"},
                                }
                            }
                        ),
                        "remoteEntry.js": "export const ok = true",
                    }
                ),
            )
        },
    )
    await request("POST", base + "/publish", headers=authorization)
    native_before = (await request("GET", base)).json()
    public = (await request("GET", docs)).json()
    assert public["sets"][0]["snapshot_id"] == first["snapshot_id"]
    root = first_record["snapshot_url"]
    entry = await request("GET", entry_url, 307)
    assert entry.headers["location"] == root
    for path, content in files.items():
        response = await request("GET", root + path)
        assert response.text == content
        assert response.headers["cache-control"] == "public, no-cache"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["origin-agent-cluster"] == "?1"
        assert "set-cookie" not in response.headers
        await request("GET", root + path, 304, headers={"If-None-Match": response.headers["etag"]})
        head = await request("HEAD", root + path)
        assert head.content == b"" and int(head.headers["content-length"]) == len(content.encode())
    assert (await request("GET", root)).text == files["index.html"]
    await request("GET", root + "guide", 308)
    assert (await request("GET", root + "guide/")).text == files["guide/index.html"]
    assert (await request("GET", root + "clean")).text == files["clean.html"]
    await request("GET", root + "missing", 404)
    await request("GET", root + "v1/publisher", 404, headers=authorization)
    await request(
        "POST",
        root + "v1/extensions/check/documentation/releases/1.0.0/documentation/global",
        405,
        headers=authorization,
    )
    await request("GET", "http://unknown.localhost/v1/extensions", 421)

    # A failed staging operation cannot move the pointer. Neither can a stale editor.
    changed_zip = archive({**files, "index.html": "Corrected page"})
    second = {**metadata(changed_zip), "expected_etag": first_record["snapshot_etag"]}

    async def fail_put(*args, **kwargs):
        raise OSError("simulated storage failure")

    with patch.object(artifacts, "put", fail_put):
        try:
            await upload(second, changed_zip)
        except OSError:
            pass
        else:
            raise AssertionError("failed storage upload unexpectedly succeeded")
    assert (await request("GET", docs)).json() == public
    second_record = (await upload(second, changed_zip)).json()
    assert second_record["snapshot_url"] != root
    assert (await request("GET", root)).text == files["index.html"]
    assert (await request("GET", second_record["snapshot_url"])).text == "Corrected page"
    await upload({**metadata(), "expected_etag": first_record["snapshot_etag"]}, expected=409)
    before_replay = (await request("GET", docs)).json()
    assert (await upload(first)).json() == first_record
    assert (await request("GET", docs)).json() == before_replay
    for change in (
        {"source_revision": "changed"},
        {"entry": "clean.html"},
        {"expected_etag": second_record["snapshot_etag"]},
    ):
        await upload({**first, **change}, expected=409)
    await upload(first, expected=409, scope="module-federation")
    await upload(
        {
            **metadata(),
            "snapshot_id": first["snapshot_id"],
            "expected_etag": second_record["snapshot_etag"],
        },
        expected=409,
    )

    # Two editors observing the same pointer cannot both win.
    async def contender():
        return await client.post(
            docs + "/global",
            headers=authorization,
            data={
                "metadata": json.dumps(
                    {**metadata(), "expected_etag": second_record["snapshot_etag"]}
                )
            },
            files={"content": ("docs.zip", zipped)},
        )

    outcomes = await asyncio.gather(contender(), contender())
    assert sorted(item.status_code for item in outcomes) == [200, 409]
    current = next(item.json() for item in outcomes if item.status_code == 200)
    assert (await request("GET", base)).json() == native_before
    await request("POST", base + "/yank", headers=authorization)
    warning = await request("GET", entry_url)
    assert "withdrawn" in warning.text and current["snapshot_url"] in warning.text
    repeated = {**metadata(), "expected_etag": current["snapshot_etag"]}
    duplicates = await asyncio.gather(upload(repeated), upload(repeated))
    assert duplicates[0].json() == duplicates[1].json()
    assert await db.DocumentationSnapshot.filter(id=repeated["snapshot_id"]).count() == 1
    await request("GET", root)

    row = await db.Release.get(extension_id="check/documentation", version="1.0.0")
    try:
        async with in_transaction():
            await db.DocumentationSet.filter(release=row).update(scope="invalid")
    except IntegrityError:
        pass
    else:
        raise AssertionError("database admitted an invalid documentation scope")
    # Bypass publish to prove the database protects pointer ownership itself.
    other_release = await db.Release.create(extension_id=row.extension_id, version="2.0.0")
    for values in ({"scope": "python"}, {"release_id": other_release.id}):
        try:
            async with in_transaction():
                await db.DocumentationSet.filter(release=row).update(**values)
        except IntegrityError:
            pass
        else:
            raise AssertionError(f"database admitted a cross-owner documentation pointer: {values}")
    # The reverse direction must also be protected while the pointer exists.
    current_set = await db.DocumentationSet.get(release=row, scope="global").select_related(
        "snapshot"
    )
    try:
        async with in_transaction():
            await db.DocumentationSnapshot.filter(id=current_set.snapshot.id).update(scope="python")
    except IntegrityError:
        pass
    else:
        raise AssertionError("database allowed a referenced snapshot to change ownership")
    await db.Release.filter(id=row.id).update(state="blocked")
    for path in (
        docs,
        private,
        entry_url,
        root,
        root + "assets/main.css",
        second_record["snapshot_url"],
    ):
        for method in ("GET", "HEAD") if path.startswith(root) else ("GET",):
            response = await request(
                method, path, 451, headers={**authorization, "If-None-Match": "*"}
            )
            assert response.headers["cache-control"] == "no-store"
    await upload(metadata(), expected=451)
    await upload(first, expected=451)

    # Inspect raw ZIP names, not normalized extraction output; no files touch disk.
    for bad in (
        "../escape.html",
        "/absolute.html",
        "a//b.html",
        "a/%2e.html",
        ".env",
        "_headers",
        "script.php",
        "a\\b.html",
    ):
        try:
            inspect_documentation(archive({"index.html": "ok", bad: "bad"}))
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe documentation member admitted: {bad}")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped_link:
        link = zipfile.ZipInfo("index.html")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zipped_link.writestr(link, "outside")
    try:
        inspect_documentation(output.getvalue())
    except ValueError:
        pass
    else:
        raise AssertionError("documentation symlink admitted")

    # A finite retry resends the candidate, never queries or adopts current.
    payload = DocumentationUpload.model_validate(
        {key: value for key, value in first.items() if key != "expected_etag"}
    )
    requests: list[httpx.Request] = []

    def recover(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("lost response", request=request)
        return httpx.Response(200, json=first_record)

    with RegistryClient(
        "http://localhost", token=token, transport=httpx.MockTransport(recover)
    ) as toolkit:
        recovered = toolkit.upload_documentation(
            "check", "documentation", "1.0.0", "global", payload, zipped
        )
        assert recovered.snapshot_id == first["snapshot_id"]
    assert [item.method for item in requests] == ["POST", "POST"]

    for unavailable in (503, 409, 200):
        attempts = 0

        def fail(request: httpx.Request, status=unavailable) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(status, json={"detail": "unavailable"})

        with RegistryClient("http://localhost", transport=httpx.MockTransport(fail)) as toolkit:
            try:
                toolkit.upload_documentation(
                    "check", "documentation", "1.0.0", "global", payload, zipped
                )
            except DocumentationOutcomeUnknown:
                assert unavailable in {503, 200} and attempts == 2
            except RegistryHTTPError:
                assert unavailable == 409 and attempts == 1
            else:
                raise AssertionError("a missing receipt must not be reported as success")
