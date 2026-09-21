from __future__ import annotations

from urllib.parse import quote

import httpx
from pydantic import ValidationError

from .contracts import PrepareReleaseRequest, ReleaseRecord
from .generated.documentation import (
    DocumentationHosting,
    DocumentationPublication,
    DocumentationReceipt,
    DocumentationUpload,
    ReleaseDocumentation,
)


class RegistryHTTPError(RuntimeError):
    def __init__(self, response: httpx.Response) -> None:
        try:
            detail = response.json().get("detail", response.text)
        except (AttributeError, ValueError):
            detail = response.text
        super().__init__(f"Registry HTTP {response.status_code}: {detail}")
        self.status_code = response.status_code
        self.response = response


class DocumentationOutcomeUnknown(RuntimeError):
    """A bounded publication attempt ended without an authoritative commit receipt."""


class RegistryClient:
    """Synchronous client for the small Extension Release control plane."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}"} if token else None,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> RegistryClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _require_success(response: httpx.Response) -> httpx.Response:
        if not response.is_success:
            raise RegistryHTTPError(response)
        return response

    @staticmethod
    def _release_path(namespace: str, name: str, version: str) -> str:
        return f"/v1/extensions/{namespace}/{name}/releases/{version}"

    def get_release(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.get(self._release_path(namespace, name, version))
        )
        return ReleaseRecord.model_validate(response.json())

    def prepare(self, namespace: str, name: str, payload: PrepareReleaseRequest) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(
                f"/v1/extensions/{namespace}/{name}/releases",
                json=payload.model_dump(mode="json", exclude_none=True),
            )
        )
        return ReleaseRecord.model_validate(response.json())

    def upload_module_federation(
        self, namespace: str, name: str, version: str, archive: bytes
    ) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(
                self._release_path(namespace, name, version) + "/module-federation",
                files={"content": ("module-federation.zip", archive, "application/zip")},
            )
        )
        return ReleaseRecord.model_validate(response.json())

    def publish(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(self._release_path(namespace, name, version) + "/publish")
        )
        return ReleaseRecord.model_validate(response.json())

    def yank(self, namespace: str, name: str, version: str, reason: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(
                self._release_path(namespace, name, version) + "/yank",
                json={"reason": reason},
            )
        )
        return ReleaseRecord.model_validate(response.json())

    def unyank(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(self._release_path(namespace, name, version) + "/unyank")
        )
        return ReleaseRecord.model_validate(response.json())

    def simple_project_url(self, project: str) -> str:
        return f"{self.base_url}/simple/{quote(project, safe='-')}/"

    def documentation_hosting(self) -> DocumentationHosting:
        response = self._require_success(self._client.get("/v1/documentation-hosting"))
        return DocumentationHosting.model_validate(response.json())

    def get_documentation(
        self, namespace: str, name: str, version: str, *, private: bool = False
    ) -> ReleaseDocumentation:
        path = self._release_path(namespace, name, version) + "/documentation"
        if private:
            path = path.replace("/v1/extensions/", "/v1/publisher/extensions/", 1)
        response = self._require_success(self._client.get(path))
        return ReleaseDocumentation.model_validate(response.json())

    def upload_documentation(
        self,
        namespace: str,
        name: str,
        version: str,
        scope: str,
        metadata: DocumentationUpload,
        archive: bytes,
        *,
        expected_etag: str | None = None,
    ) -> DocumentationReceipt:
        """Try the saved publication at most twice; never infer success from current."""
        from .documentation import inspect_documentation

        inspected = inspect_documentation(archive, metadata.entry)
        if inspected.digest != metadata.content_sha256:
            raise ValueError("saved documentation archive no longer matches its metadata")
        publication = DocumentationPublication.model_validate(
            {**metadata.model_dump(mode="json"), "expected_etag": expected_etag}
        )
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                response = self._require_success(
                    self._client.post(
                        self._release_path(namespace, name, version) + f"/documentation/{scope}",
                        data={"metadata": publication.model_dump_json()},
                        files={"content": ("documentation.zip", archive, "application/zip")},
                    )
                )
                return DocumentationReceipt.model_validate_json(response.content)
            except (httpx.TransportError, RegistryHTTPError, ValidationError) as error:
                if isinstance(error, RegistryHTTPError) and error.status_code not in {
                    500,
                    502,
                    503,
                    504,
                }:
                    raise
                last_error = error
        raise DocumentationOutcomeUnknown(
            f"Publication {metadata.snapshot_id} outcome is unknown after two attempts; "
            "keep and retry the same saved candidate. Do not refresh its ETag or snapshot ID."
        ) from last_error
