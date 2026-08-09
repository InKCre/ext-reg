from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote

import httpx

from .contracts.models import ReleaseRecord, TargetAssociation, TargetRecord, validate_relative_path


class RegistryHTTPError(RuntimeError):
    def __init__(self, response: httpx.Response) -> None:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        super().__init__(f"Registry HTTP {response.status_code}: {detail}")
        self.status_code = response.status_code
        self.response = response


class RegistryReleaseStateError(RuntimeError):
    pass


class RegistryClient:
    """Small synchronous client for public resolution and publisher operations."""

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

    def get_release(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.get(f"/v1/extensions/{namespace}/{name}/versions/{version}")
        )
        release = ReleaseRecord.model_validate(response.json())
        if release.state != "published":
            raise RegistryReleaseStateError(
                f"Registry release is not installable (state: {release.state})"
            )
        return release

    def put_blob(self, digest: str, content: bytes, media_type: str) -> None:
        response = self._client.put(
            f"/v1/blobs/{quote(digest, safe=':')}",
            content=content,
            headers={"Content-Type": media_type},
        )
        self._require_success(response)

    def put_target(
        self,
        namespace: str,
        name: str,
        version: str,
        target_key: str,
        association: TargetAssociation,
    ) -> TargetRecord:
        response = self._require_success(
            self._client.put(
                f"/v1/extensions/{namespace}/{name}/versions/{version}/targets/{target_key}",
                json=association.model_dump(mode="json"),
            )
        )
        return TargetRecord.model_validate(response.json())

    def publish(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(f"/v1/extensions/{namespace}/{name}/versions/{version}/publish")
        )
        return ReleaseRecord.model_validate(response.json())

    def yank(self, namespace: str, name: str, version: str) -> ReleaseRecord:
        response = self._require_success(
            self._client.post(f"/v1/extensions/{namespace}/{name}/versions/{version}/yank")
        )
        return ReleaseRecord.model_validate(response.json())

    def artifact_manifest_url(self, target_digest: str) -> str:
        return f"{self.base_url}/v1/artifacts/{quote(target_digest, safe=':')}/manifest"

    def artifact_file_url(self, target_digest: str, relative_path: str) -> str:
        path = PurePosixPath(validate_relative_path(relative_path)).as_posix()
        encoded = quote(path, safe="/")
        return f"{self.base_url}/v1/artifacts/{quote(target_digest, safe=':')}/files/{encoded}"
