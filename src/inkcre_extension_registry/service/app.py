from __future__ import annotations

import base64
import binascii
import hashlib
import mimetypes
import re
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from packaging.version import InvalidVersion
from packaging.version import Version as Pep440Version
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from .. import __version__
from ..contracts.models import (
    ExtensionRecord,
    ExtensionSummary,
    PrepareReleaseRequest,
    PythonEntryPoint,
    RegistrySegment,
    ReleaseRecord,
    StrictSemVer,
    YankRequest,
    normalize_project_name,
    validate_segment,
    validate_version,
)
from .module_federation import (
    ModuleFederationValidationError,
    inspect_module_federation_snapshot,
    validate_relative_asset_path,
)
from .python_distribution import (
    DistributionValidationError,
    inspect_wheel,
    semver_to_pep440,
    sha256_hex,
)
from .repository import (
    PublicObject,
    RegistryBlockedError,
    RegistryConflictError,
    RegistryNotFoundError,
    RegistryRepository,
    RegistryStateError,
)
from .simple import (
    SIMPLE_HTML,
    SIMPLE_JSON,
    negotiate_simple,
    project_html,
    project_json,
    root_html,
    root_json,
)
from .ui import extension_catalog_html

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MultiPartParser.spool_max_size = MAX_UPLOAD_BYTES + 1

BEARER_PATTERN = re.compile(r"^Bearer ([A-Za-z0-9._~-]{24,512})$")
UPLOAD_PATH_PATTERN = re.compile(
    r"^/legacy/$|^/v1/extensions/[^/]+/[^/]+/releases/[^/]+/module-federation$"
)


def _repository(request: Request) -> RegistryRepository:
    return RegistryRepository(request.scope["env"])


def _credential_from_authorization(authorization: str | None) -> str | None:
    bearer = BEARER_PATTERN.fullmatch(authorization or "")
    if bearer is not None:
        return bearer.group(1)
    if not authorization or not authorization.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    username, token = decoded.split(":", 1)
    if username != "__token__" or not 24 <= len(token) <= 512:
        return None
    return token


async def _publisher_namespace(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    token = _credential_from_authorization(authorization)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "publisher credential required")
    namespace = await _repository(request).authenticate(hashlib.sha256(token.encode()).hexdigest())
    if namespace is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid publisher credential")
    requested_namespace = request.path_params.get("namespace")
    if requested_namespace is not None and namespace != requested_namespace:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "credential does not own namespace")
    return namespace


def _validate_identity(namespace: str, name: str, version: str | None = None) -> str:
    try:
        validate_segment(namespace)
        validate_segment(name)
        if version is not None:
            validate_version(version)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    return f"{namespace}/{name}"


def _map_repository_error(error: Exception) -> HTTPException:
    if isinstance(error, RegistryBlockedError):
        return HTTPException(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, str(error))
    if isinstance(error, RegistryConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    if isinstance(error, RegistryNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, RegistryStateError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    raise error


def _public_origin(request: Request) -> str:
    value = getattr(request.scope["env"], "PUBLIC_ORIGIN", None)
    if not isinstance(value, str):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "canonical PUBLIC_ORIGIN binding is required",
        )
    parsed = urlparse(value)
    local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if (
        (parsed.scheme != "https" and not local_http)
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PUBLIC_ORIGIN must be an absolute HTTPS origin",
        )
    return value.rstrip("/")


async def _form(request: Request) -> Any:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "multipart/form-data required")
    try:
        return await request.form(max_files=1, max_fields=64, max_part_size=MAX_UPLOAD_BYTES)
    except Exception as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid multipart upload") from error


def _form_string(form: Any, name: str, *, required: bool = True) -> str | None:
    value = form.get(name)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"multipart field {name!r} is required")
    return value


async def _read_public_object(
    repository: RegistryRepository, descriptor: PublicObject | None
) -> tuple[bytes, PublicObject]:
    if descriptor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Distribution file does not exist")
    stored = await repository.artifacts.get(descriptor.r2_key)
    if stored is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Distribution bytes unavailable")
    body = stored.body
    if not isinstance(body, bytes):
        try:
            body = bytes(body)
        except (TypeError, ValueError) as error:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Distribution bytes unavailable"
            ) from error
    return body, descriptor


def create_app() -> FastAPI:
    app = FastAPI(
        title="InKCre Extension Registry",
        version=__version__,
        description="Extension Releases with native Python and Module Federation distribution.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "OPTIONS", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def bound_uploads(request: Request, call_next: Any) -> Response:
        if request.method == "POST" and UPLOAD_PATH_PATTERN.fullmatch(request.url.path):
            content_length = request.headers.get("content-length")
            if (
                content_length is None
                or "chunked" in request.headers.get("transfer-encoding", "").lower()
            ):
                return JSONResponse(
                    status_code=status.HTTP_411_LENGTH_REQUIRED,
                    content={"detail": "Content-Length is required for uploads"},
                )
            try:
                declared_length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Content-Length must be an integer"},
                )
            if declared_length < 1 or declared_length > MAX_UPLOAD_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "multipart upload exceeds 20 MiB"},
                )
        response = await call_next(request)
        if response.status_code in {
            status.HTTP_404_NOT_FOUND,
            status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
        }:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/livez")
    async def livez() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def extension_catalog(request: Request) -> HTMLResponse:
        extensions = await _repository(request).list_extensions()
        response = HTMLResponse(extension_catalog_html(extensions))
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/v1/extensions", response_model=list[ExtensionSummary])
    async def list_extensions(request: Request, response: Response) -> list[ExtensionSummary]:
        response.headers["Cache-Control"] = "no-store"
        return await _repository(request).list_extensions()

    @app.get("/v1/extensions/{namespace}/{name}", response_model=ExtensionRecord)
    async def get_extension(
        namespace: RegistrySegment, name: RegistrySegment, request: Request, response: Response
    ) -> ExtensionRecord:
        extension_name = _validate_identity(namespace, name)
        extension = await _repository(request).get_extension(extension_name)
        if extension is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Extension does not exist")
        response.headers["Cache-Control"] = "no-store"
        return extension

    @app.get(
        "/v1/extensions/{namespace}/{name}/releases/{version}",
        response_model=ReleaseRecord,
    )
    async def get_release(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        request: Request,
        response: Response,
    ) -> ReleaseRecord:
        extension_name = _validate_identity(namespace, name, version)
        try:
            release = await _repository(request).get_release(extension_name, version)
        except Exception as error:
            raise _map_repository_error(error) from error
        if release is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "public Release does not exist")
        response.headers["Cache-Control"] = "no-store"
        return release

    @app.post(
        "/v1/extensions/{namespace}/{name}/releases",
        response_model=ReleaseRecord,
    )
    async def prepare_release(
        namespace: RegistrySegment,
        name: RegistrySegment,
        payload: PrepareReleaseRequest,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        _validate_identity(namespace, name, payload.version)
        try:
            return await _repository(request).prepare_release(namespace, name, payload)
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post(
        "/v1/extensions/{namespace}/{name}/releases/{version}/publish",
        response_model=ReleaseRecord,
    )
    async def publish_release(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        extension_name = _validate_identity(namespace, name, version)
        try:
            return await _repository(request).publish(extension_name, version)
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post(
        "/v1/extensions/{namespace}/{name}/releases/{version}/yank",
        response_model=ReleaseRecord,
    )
    async def yank_release(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
        payload: YankRequest | None = None,
    ) -> ReleaseRecord:
        extension_name = _validate_identity(namespace, name, version)
        try:
            return await _repository(request).yank(
                extension_name,
                version,
                (payload or YankRequest()).reason,
            )
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post(
        "/v1/extensions/{namespace}/{name}/releases/{version}/unyank",
        response_model=ReleaseRecord,
    )
    async def unyank_release(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        extension_name = _validate_identity(namespace, name, version)
        try:
            return await _repository(request).unyank(extension_name, version)
        except Exception as error:
            raise _map_repository_error(error) from error

    @app.post("/legacy/", status_code=status.HTTP_200_OK)
    async def legacy_upload(
        request: Request,
        namespace: Annotated[str, Depends(_publisher_namespace)],
    ) -> Response:
        form = await _form(request)
        try:
            action = _form_string(form, ":action")
            protocol_version = _form_string(form, "protocol_version")
            if action != "file_upload" or protocol_version != "1":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "unsupported legacy upload protocol"
                )
            upload = form.get("content")
            if not isinstance(upload, UploadFile) or not upload.filename:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "content file is required")
            content = await upload.read()
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "file exceeds 20 MiB")
            form_name = _form_string(form, "name")
            form_version = _form_string(form, "version")
            form_filetype = _form_string(form, "filetype")
            form_metadata_version = _form_string(form, "metadata_version")
            claimed_sha256 = _form_string(form, "sha256_digest")
            if form_filetype != "bdist_wheel":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "only wheels are accepted in MVP")
            try:
                normalized_project = normalize_project_name(form_name or "")
                form_version_literal = form_version or ""
                pep440_version = Pep440Version(form_version_literal)
            except (ValueError, InvalidVersion) as error:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "invalid Python upload identity"
                ) from error
            distribution = await _repository(request).prepared_python_distribution(
                namespace, normalized_project, form_version_literal
            )
            if distribution is None:
                candidates = await _repository(request).prepared_python_distributions(
                    namespace, normalized_project
                )
                distribution = next(
                    (
                        candidate
                        for candidate in candidates
                        if Pep440Version(semver_to_pep440(candidate.release_version))
                        == pep440_version
                    ),
                    None,
                )
            if distribution is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    "no unique prepared Python Project/version association exists",
                )
            try:
                expected_pep440_literal = semver_to_pep440(distribution.release_version)
                if (
                    form_version_literal != expected_pep440_literal
                    or distribution.project_version != expected_pep440_literal
                    or pep440_version != Pep440Version(expected_pep440_literal)
                ):
                    raise DistributionValidationError(
                        "upload version must use the Release's canonical PEP 440 spelling"
                    )
                inspected = inspect_wheel(
                    upload.filename,
                    content,
                    expected_project=distribution.normalized_project,
                    expected_release_version=distribution.release_version,
                    expected_entry_point=PythonEntryPoint(
                        group=distribution.entry_group,
                        name=distribution.entry_name,
                        object=distribution.entry_object,
                    ),
                )
            except (DistributionValidationError, InvalidVersion, ValueError) as error:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
            digest = sha256_hex(content)
            metadata_digest = sha256_hex(inspected.metadata)
            if claimed_sha256 != digest:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "claimed SHA-256 does not match wheel"
                )
            if inspected.metadata_version != form_metadata_version:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "form metadata_version does not match wheel Core Metadata",
                )
            try:
                await _repository(request).put_python_file(
                    distribution,
                    filename=upload.filename,
                    content=content,
                    sha256=digest,
                    filetype=form_filetype,
                    requires_python=inspected.requires_python,
                    metadata=inspected.metadata,
                    metadata_sha256=metadata_digest,
                )
            except Exception as error:
                raise _map_repository_error(error) from error
        finally:
            await form.close()
        return Response(status_code=status.HTTP_200_OK)

    @app.post(
        "/v1/extensions/{namespace}/{name}/releases/{version}/module-federation",
        response_model=ReleaseRecord,
    )
    async def upload_module_federation(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        request: Request,
        _publisher: Annotated[str, Depends(_publisher_namespace)],
    ) -> ReleaseRecord:
        extension_name = _validate_identity(namespace, name, version)
        form = await _form(request)
        try:
            upload = form.get("content")
            if not isinstance(upload, UploadFile):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "content ZIP file is required")
            content = await upload.read()
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "file exceeds 20 MiB")
            public_prefix = (
                _public_origin(request)
                + f"/extensions/{extension_name}/{version}/module-federation/"
            )
            try:
                snapshot = inspect_module_federation_snapshot(content, public_prefix=public_prefix)
                return await _repository(request).put_module_federation_snapshot(
                    extension_name,
                    version,
                    snapshot.snapshot_hash,
                    snapshot.files,
                    snapshot.media_types,
                )
            except ModuleFederationValidationError as error:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
            except Exception as error:
                raise _map_repository_error(error) from error
        finally:
            await form.close()

    @app.get("/simple/")
    async def simple_root(request: Request) -> Response:
        media_type = negotiate_simple(request.headers.get("accept"))
        if media_type is None:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, "unsupported Simple media type")
        projects = await _repository(request).simple_projects()
        headers = {"Vary": "Accept", "Cache-Control": "no-store"}
        if media_type == SIMPLE_JSON:
            return JSONResponse(root_json(projects), media_type=SIMPLE_JSON, headers=headers)
        return HTMLResponse(root_html(projects), media_type=SIMPLE_HTML, headers=headers)

    @app.get("/simple/{project}/")
    async def simple_project(project: str, request: Request) -> Response:
        try:
            normalized_project = normalize_project_name(project)
        except ValueError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project does not exist") from error
        if project != normalized_project:
            return Response(
                status_code=status.HTTP_308_PERMANENT_REDIRECT,
                headers={"Location": f"/simple/{normalized_project}/"},
            )
        files = await _repository(request).simple_files(normalized_project)
        if not files:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project does not exist")
        media_type = negotiate_simple(request.headers.get("accept"))
        if media_type is None:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, "unsupported Simple media type")
        headers = {"Vary": "Accept", "Cache-Control": "no-store"}
        if media_type == SIMPLE_JSON:
            return JSONResponse(
                project_json(normalized_project, files), media_type=SIMPLE_JSON, headers=headers
            )
        return HTMLResponse(project_html(files), media_type=SIMPLE_HTML, headers=headers)

    @app.get("/packages/{project}/{project_version}/{filename}")
    async def python_file(
        project: str, project_version: str, filename: str, request: Request
    ) -> Response:
        try:
            normalized_project = normalize_project_name(project)
            metadata = filename.endswith(".metadata")
            archive_filename = filename.removesuffix(".metadata") if metadata else filename
            descriptor = await _repository(request).python_public_file(
                normalized_project,
                project_version,
                archive_filename,
                metadata=metadata,
            )
            body, public = await _read_public_object(_repository(request), descriptor)
        except Exception as error:
            if isinstance(error, HTTPException):
                raise
            raise _map_repository_error(error) from error
        return Response(
            content=body,
            media_type=public.media_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=31536000, immutable",
                "ETag": f'"{public.etag}"',
            },
        )

    @app.get("/extensions/{namespace}/{name}/{version}/module-federation/{relative_path:path}")
    async def module_federation_file(
        namespace: RegistrySegment,
        name: RegistrySegment,
        version: StrictSemVer,
        relative_path: str,
        request: Request,
    ) -> Response:
        extension_name = _validate_identity(namespace, name, version)
        try:
            validate_relative_asset_path(relative_path)
            media_type = (
                "application/json"
                if relative_path == "mf-manifest.json"
                else mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
            )
            descriptor = await _repository(request).module_federation_public_file(
                extension_name, version, relative_path, media_type
            )
            body, public = await _read_public_object(_repository(request), descriptor)
        except ModuleFederationValidationError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "asset does not exist") from error
        except Exception as error:
            if isinstance(error, HTTPException):
                raise
            raise _map_repository_error(error) from error
        return Response(
            content=body,
            media_type=public.media_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=31536000, immutable",
                "ETag": f'"{public.etag}"',
            },
        )

    return app


app = create_app()
