from __future__ import annotations

from urllib.parse import quote

import httpx

from .contracts import PrepareReleaseRequest, ReleaseRecord
from .generated.documentation import (
    DocumentationHosting,
    DocumentationRecord,
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
    ) -> DocumentationRecord:
        """Recover only an exact matching result without refreshing the precondition."""
        from .documentation import inspect_documentation

        inspected = inspect_documentation(archive, metadata.entry)
        if inspected.digest != metadata.content_sha256:
            raise ValueError("saved documentation archive no longer matches its metadata")
        try:
            response = self._require_success(
                self._client.put(
                    self._release_path(namespace, name, version) + f"/documentation/{scope}",
                    headers={"If-Match": expected_etag}
                    if expected_etag
                    else {"If-None-Match": "*"},
                    data={"metadata": metadata.model_dump_json()},
                    files={"content": ("documentation.zip", archive, "application/zip")},
                )
            )
            return DocumentationRecord.model_validate(response.json())
        except (httpx.TransportError, RegistryHTTPError) as error:
            if isinstance(error, RegistryHTTPError) and error.status_code not in {
                409,
                412,
                500,
                502,
                503,
                504,
            }:
                raise
            try:
                current = self.get_documentation(namespace, name, version, private=True)
            except (httpx.TransportError, RegistryHTTPError):
                raise error from None
            for item in current.sets:
                if item.scope == scope and all(
                    item.model_dump(mode="json")[key] == value
                    for key, value in metadata.model_dump(mode="json").items()
                ):
                    return item
            # A successful concurrent replacement is not ours to overwrite.
            raise
