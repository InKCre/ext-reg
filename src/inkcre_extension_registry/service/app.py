from __future__ import annotations

import hashlib
import re
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..contracts.models import (
    DIGEST_PATTERN,
    ReleaseRecord,
    TargetAssociation,
    TargetManifest,
    TargetRecord,
    validate_segment,
    validate_target_key,
    validate_version,
)
from .repository import (
    RegistryConflictError,
    RegistryNotFoundError,
    RegistryRepository,
    RegistryStateError,
)

MAX_BLOB_BYTES = 20 * 1024 * 1024
BEARER_PATTERN = re.compile(r"^Bearer ([A-Za-z0-9._~-]{24,512})$")


def _repository(request: Request) -> RegistryRepository:
    return RegistryRepository(request.scope["env"])


async def _publisher_namespace(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    match = BEARER_PATTERN.fullmatch(authorization or "")
    if match is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "publisher bearer credential required")
    token_hash = hashlib.sha256(match.group(1).encode()).hexdigest()
    namespace = await _repository(request).authenticate(token_hash)
    if namespace is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid publisher credential")
    requested_namespace = request.path_params.get("namespace")
    if requested_namespace is not None and namespace != requested_namespace:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "credential does not own namespace")
    return namespace


def _validate_identity(namespace: str, name: str, version: str | None = None) -> None:
    try:
        validate_segment(namespace)
        validate_segment(name)
        if version is not None:
            validate_version(version)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


def _map_repository_error(error: Exception) -> HTTPException:
    if isinstance(error, RegistryConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    if isinstance(error, RegistryNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, RegistryStateError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    raise error


def create_app() -> FastAPI:
    app = FastAPI(
        title="InKCre Extension Registry",
        version=__version__,
        description="Public metadata/artifact reads and scoped Extension target publication.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "OPTIONS", "PUT", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/livez")
    async def livez() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/extensions")
    async def list_extensions(request: Request) -> list[dict[str, str]]:
        return await _repository(request).list_extensions()

    @app.get("/v1/extensions/{namespace}/{name}")
    async def get_extension(namespace: str, name: str, request: Request) -> dict[str, Any]:
        _validate_identity(namespace, name)
        versions = await _repository(request).extension_versions(namespace, name)
        if not versions:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "extension does not exist")
        return {
            "namespace": namespace,
            "name": name,
            "versions": [release.model_dump(mode="json") for release in versions],
        }

    @app.get(
        "/v1/extensions/{namespace}/{name}/versions/{version}",
        response_model=ReleaseRecord,
    )
    async def get_release(
        namespace: str, name: str, version: str, request: Request
    ) -> ReleaseRecord:
        _validate_identity(namespace, name, version)
        release = await _repository(request).get_release(namespace, name, version)
        if release is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "published release does not exist")
        return release

    @app.put("/v1/blobs/{digest}", status_code=status.HTTP_204_NO_CONTENT)
    async def put_blob(
        digest: str,
        request: Request,
        _namespace: Annotated[str, Depends(_publisher_namespace)],
        content_type: Annotated[str | None, Header()] = None,
    ) -> Response:
        if not DIGEST_PATTERN.fullmatch(digest):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid SHA-256 digest")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_BLOB_BYTES:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        "blob exceeds 20 MiB",
                    )
            except ValueError as error:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "invalid content length",
                ) from error
        content = await request.body()
        if len(content) > MAX_BLOB_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "blob exceeds 20 MiB")
        actual = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if actual != digest:
            raise HTTPException(status.HTTP_409_CONFLICT, "blob digest mismatch")
        try:
            await _repository(request).put_blob(
                digest,
                content,
                content_type or "application/octet-stream",
            )
        except Exception as error:
            raise _map_repository_error(error) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.put(
        "/v1/extensions/{namespace}/{name}/versions/{version}/targets/{target_key}",
        response_model=TargetRecord,
    )
    async def put_target(
        namespace: str,
        name: str,
        version: str,
        target_key: str,
        association: TargetAssociation,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> TargetRecord:
        _validate_identity(namespace, name, version)
        try:
            validate_target_key(target_key)
            return await _repository(request).put_target(
                namespace,
                name,
                version,
                target_key,
                association,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post(
        "/v1/extensions/{namespace}/{name}/versions/{version}/publish",
        response_model=ReleaseRecord,
    )
    async def publish_release(
        namespace: str,
        name: str,
        version: str,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        _validate_identity(namespace, name, version)
        try:
            return await _repository(request).publish(namespace, name, version)
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post(
        "/v1/extensions/{namespace}/{name}/versions/{version}/yank",
        response_model=ReleaseRecord,
    )
    async def yank_release(
        namespace: str,
        name: str,
        version: str,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        _validate_identity(namespace, name, version)
        try:
            return await _repository(request).yank(namespace, name, version)
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.get("/v1/artifacts/{target_digest}/manifest", response_model=TargetManifest)
    async def get_target_manifest(
        target_digest: str, request: Request, response: Response
    ) -> TargetManifest:
        if not DIGEST_PATTERN.fullmatch(target_digest):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid target digest")
        try:
            manifest = await _repository(request).target_manifest(target_digest)
        except Exception as error:
            raise _map_repository_error(error) from error
        if manifest is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "artifact does not exist")
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["ETag"] = f'"{target_digest}"'
        return manifest

    return app


app = create_app()
