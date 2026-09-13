"""R2 access through the standard S3 SDK, with blocking I/O off the event loop."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import anyio
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class StoredObject:
    size: int


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
