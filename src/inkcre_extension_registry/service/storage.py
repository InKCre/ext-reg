"""R2 access through the standard S3 SDK, with blocking I/O off the event loop."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from dataclasses import dataclass

import anyio
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .errors import RegistryConflictError


@dataclass(frozen=True)
class StoredObject:
    size: int


@dataclass(frozen=True)
class Artifact:
    key: str
    content: bytes
    media_type: str


class ArtifactStore:
    def __init__(self, endpoint_url: str, bucket: str) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name="auto",
            config=Config(
                connect_timeout=10,
                read_timeout=30,
                max_pool_connections=10,
                retries={"mode": "standard", "total_max_attempts": 3},
                s3={"addressing_style": "path"},
            ),
        )

    async def close(self) -> None:
        await anyio.to_thread.run_sync(self.client.close)

    async def head(self, key: str) -> StoredObject | None:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: self.client.head_object(Bucket=self.bucket, Key=key)
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return StoredObject(size=result["ContentLength"])

    async def put(self, key: str, content: bytes, *, content_type: str) -> None:
        await anyio.to_thread.run_sync(
            lambda: self.client.put_object(
                Bucket=self.bucket, Key=key, Body=content, ContentType=content_type
            )
        )

    async def ensure(self, key: str, content: bytes, media_type: str) -> None:
        """Stage immutable bytes; an existing key must have the expected size."""
        stored = await self.head(key)
        if stored is not None and stored.size != len(content):
            raise RegistryConflictError("staging object size conflict")
        if stored is None:
            await self.put(key, content, content_type=media_type)

    def batch(self, *, concurrency: int) -> ArtifactBatch:
        """Create one capacity group; retain it across requests that share a budget."""
        return ArtifactBatch(self, concurrency=concurrency)

    async def open(self, key: str):
        try:
            return await anyio.to_thread.run_sync(
                lambda: self.client.get_object(Bucket=self.bucket, Key=key)
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    @staticmethod
    async def stream(body) -> AsyncIterator[bytes]:
        try:
            while chunk := await anyio.to_thread.run_sync(body.read, 64 * 1024):
                yield chunk
        finally:
            # Close even if the response is cancelled by a disconnect.
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(body.close)


class ArtifactBatch:
    """Bounded object operations sharing one owner's capacity, independent of other groups."""

    def __init__(self, store: ArtifactStore, *, concurrency: int) -> None:
        self._store = store
        self._capacity = anyio.CapacityLimiter(concurrency)
        self._workers = concurrency

    async def ensure_many(self, artifacts: Iterable[Artifact]) -> None:
        async def stage(artifact: Artifact) -> bool:
            async with self._capacity:
                await self._store.ensure(artifact.key, artifact.content, artifact.media_type)
            return True

        await self._all(artifacts, stage)

    async def available(self, keys: Iterable[str]) -> bool:
        async def exists(key: str) -> bool:
            async with self._capacity:
                return await self._store.head(key) is not None

        return await self._all(keys, exists)

    async def _all[T](self, items: Iterable[T], operation: Callable[[T], Awaitable[bool]]) -> bool:
        remaining = iter(items)
        complete = True
        failure: Exception | None = None

        async def worker() -> None:
            nonlocal complete, failure
            try:
                for item in remaining:
                    if not await operation(item):
                        complete = False
                        group.cancel_scope.cancel()
                        return
            except Exception as error:
                failure = failure or error
                group.cancel_scope.cancel()

        async with anyio.create_task_group() as group:
            for _ in range(self._workers):
                group.start_soon(worker)
        # Leave the task group before raising so siblings finish cleanup and the
        # original domain error retains its HTTP mapping instead of becoming a group.
        if failure is not None:
            raise failure
        return complete
