from __future__ import annotations

import mimetypes
from urllib.parse import unquote, urlparse

from workers import Response, WorkerEntrypoint

from .contracts.models import normalize_project_name, validate_segment, validate_version
from .service.app import app
from .service.module_federation import validate_relative_asset_path
from .service.repository import RegistryBlockedError, RegistryRepository


class Default(WorkerEntrypoint):
    @staticmethod
    def _unavailable(message="not found", *, status=404):
        return Response(message, status=status, headers={"Cache-Control": "no-store"})

    async def _stored_response(self, request, descriptor):
        if descriptor is None:
            return self._unavailable()
        stored = await RegistryRepository(self.env).artifacts.get(descriptor.r2_key)
        if stored is None:
            return self._unavailable("Distribution bytes unavailable", status=503)
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Type": descriptor.media_type,
            "ETag": f'"{descriptor.etag}"',
        }
        body = None if request.method == "HEAD" else stored.body
        return Response(body, headers=headers)

    async def fetch(self, request):
        parsed = urlparse(request.url)
        repository = RegistryRepository(self.env)
        if request.method in {"GET", "HEAD"} and parsed.path.startswith("/packages/"):
            parts = parsed.path.removeprefix("/packages/").split("/")
            if len(parts) != 3:
                return self._unavailable()
            project, project_version, filename = (unquote(part) for part in parts)
            metadata = filename.endswith(".metadata")
            archive_filename = filename.removesuffix(".metadata") if metadata else filename
            try:
                normalized_project = normalize_project_name(project)
                if normalized_project != project or not archive_filename:
                    return self._unavailable()
                descriptor = await repository.python_public_file(
                    normalized_project,
                    project_version,
                    archive_filename,
                    metadata=metadata,
                )
                return await self._stored_response(request, descriptor)
            except (ValueError, RegistryBlockedError) as error:
                status = 451 if isinstance(error, RegistryBlockedError) else 404
                return self._unavailable(str(error), status=status)

        prefix = "/extensions/"
        if request.method in {"GET", "HEAD"} and parsed.path.startswith(prefix):
            parts = parsed.path.removeprefix(prefix).split("/", 4)
            if len(parts) != 5 or parts[3] != "module-federation":
                return self._unavailable()
            namespace, name, version, _kind, encoded_path = parts
            relative_path = unquote(encoded_path)
            try:
                validate_segment(namespace)
                validate_segment(name)
                validate_version(version)
                validate_relative_asset_path(relative_path)
                media_type = (
                    "application/json"
                    if relative_path == "mf-manifest.json"
                    else mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
                )
                descriptor = await repository.module_federation_public_file(
                    f"{namespace}/{name}", version, relative_path, media_type
                )
                return await self._stored_response(request, descriptor)
            except (ValueError, RegistryBlockedError) as error:
                status = 451 if isinstance(error, RegistryBlockedError) else 404
                return self._unavailable(str(error), status=status)

        import asgi

        return await asgi.fetch(app, request.js_object, self.env)
