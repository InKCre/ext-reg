from __future__ import annotations

from urllib.parse import quote

import httpx

from .contracts import PrepareReleaseRequest, ReleaseRecord


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
