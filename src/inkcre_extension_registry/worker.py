from __future__ import annotations

from urllib.parse import unquote, urlparse

from workers import Response, WorkerEntrypoint

from .contracts.models import DIGEST_PATTERN, validate_relative_path
from .service.app import app
from .service.repository import RegistryRepository, RegistryStateError


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        marker = "/files/"
        artifact_prefix = "/v1/artifacts/"
        if parsed.path.startswith(artifact_prefix) and marker in parsed.path:
            digest_and_path = parsed.path.removeprefix(artifact_prefix)
            target_digest, encoded_path = digest_and_path.split(marker, 1)
            relative_path = unquote(encoded_path)
            if not DIGEST_PATTERN.fullmatch(target_digest):
                return Response("invalid target digest", status=422)
            try:
                validate_relative_path(relative_path)
                repository = RegistryRepository(self.env)
                descriptor = await repository.artifact_file(target_digest, relative_path)
                if descriptor is None:
                    return Response("not found", status=404)
                stored = await repository.artifacts.get(descriptor.blob_key)
                if stored is None or int(stored.size) != descriptor.size:
                    return Response("artifact bytes unavailable", status=503)
                return Response(
                    stored.body,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "Content-Type": descriptor.media_type,
                        "ETag": f'"{target_digest}"',
                    },
                )
            except ValueError:
                return Response("invalid artifact path", status=422)
            except RegistryStateError:
                return Response("artifact blocked", status=451)

        import asgi

        return await asgi.fetch(app, request.js_object, self.env)
