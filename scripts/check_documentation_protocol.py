"""Frozen v2 candidate identities and client recovery, without Registry, PostgreSQL or S3."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx
from inkcre_extension_toolkit.client import (
    DocumentationOutcomeUnknown,
    RegistryClient,
    RegistryHTTPError,
)
from inkcre_extension_toolkit.documentation import (
    DocumentationCandidate,
    documentation_fingerprint,
    inspect_documentation,
)

FIXTURE = Path(__file__).with_name("fixtures") / "documentation-v2.json"


def fixture_archive(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def check_client(candidate: DocumentationCandidate, archive: bytes, receipt: dict) -> None:
    namespace, name = candidate.name.split("/", 1)

    def upload(transport):
        with RegistryClient("https://registry.invalid", transport=transport) as client:
            return client.upload_documentation(
                namespace,
                name,
                candidate.version,
                candidate.scope,
                candidate.metadata,
                archive,
                expected_etag=candidate.expected_etag,
                distribution=candidate.distribution,
            )

    requests: list[httpx.Request] = []

    def recover(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("lost response", request=request)
        return httpx.Response(200, json=receipt)

    assert upload(httpx.MockTransport(recover)).snapshot_etag == receipt["snapshot_etag"]
    assert [request.method for request in requests] == ["POST", "POST"]
    # Multipart boundary tokens may vary; the saved publication and ZIP must not.
    for request in requests:
        assert archive in request.content
        assert candidate.metadata.snapshot_id.encode() in request.content
        expected = json.dumps(candidate.expected_etag, separators=(",", ":")).encode()
        assert b'"expected_etag":' + expected in request.content

    for status, invalid in ((503, None), (409, None), (200, {})):
        attempts = 0

        def fail(request: httpx.Request, status=status, invalid=invalid) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(status, json=invalid or {"detail": "unavailable"})

        try:
            upload(httpx.MockTransport(fail))
        except DocumentationOutcomeUnknown:
            assert status in {503, 200} and attempts == 2
        except RegistryHTTPError:
            assert status == 409 and attempts == 1
        else:
            raise AssertionError("unknown or rejected publication was reported as successful")

    for field, value in (
        ("distribution", "python" if candidate.distribution != "python" else "module_federation"),
        ("content_sha256", "f" * 64),
        ("snapshot_etag", '"' + "f" * 64 + '"'),
    ):
        attempts = 0

        def wrong_receipt(request: httpx.Request, field=field, value=value) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(200, json={**receipt, field: value})

        try:
            upload(httpx.MockTransport(wrong_receipt))
        except DocumentationOutcomeUnknown:
            assert attempts == 2, field
        else:
            raise AssertionError(f"receipt with incorrect {field} reported success")


def main() -> None:
    fixture = json.loads(FIXTURE.read_text())
    archive = fixture_archive(fixture["files"])
    for vector in fixture["vectors"]:
        candidate = DocumentationCandidate.model_validate(vector["candidate"])
        metadata = candidate.metadata.model_dump(mode="json")
        assert (
            inspect_documentation(archive, candidate.metadata.entry).digest
            == metadata["content_sha256"]
        )
        expected = vector["fingerprint"]
        # This expected JSON/hash was captured from the pre-refactor protocol. Do not
        # derive it through the function under test or regenerate it during checks.
        assert hashlib.sha256(vector["canonical_json"].encode()).hexdigest() == expected
        arguments = (candidate.name, candidate.distribution, candidate.version, candidate.scope)
        assert documentation_fingerprint(*arguments, metadata, candidate.expected_etag) == expected
        assert (
            documentation_fingerprint(
                *arguments, vector["candidate"]["metadata"], candidate.expected_etag
            )
            == expected
        ), "saved candidates with omitted default fields changed identity"
        assert (
            documentation_fingerprint(
                *arguments, {**metadata, "future_non_identity_field": None}, candidate.expected_etag
            )
            == expected
        ), "DTO additions must not implicitly extend the v2 identity"
        changed_precondition = None if candidate.expected_etag else '"' + "a" * 64 + '"'
        assert documentation_fingerprint(*arguments, metadata, changed_precondition) != expected
        assert (
            documentation_fingerprint(
                candidate.name,
                candidate.distribution,
                "2.0.0",
                candidate.scope,
                metadata,
                candidate.expected_etag,
            )
            != expected
        )
        receipt = {
            **metadata,
            "name": candidate.name,
            "distribution": candidate.distribution,
            "version": candidate.version,
            "scope": candidate.scope,
            "snapshot_etag": f'"{expected}"',
            "snapshot_url": f"https://{candidate.metadata.snapshot_id}.docs.invalid/",
            "committed_at": "2026-10-13T00:00:00+00:00",
        }
        check_client(candidate, archive, receipt)
    print(
        "Frozen v2 candidates, omitted defaults, Unicode, corrections and bounded recovery passed."
    )


if __name__ == "__main__":
    main()
