"""Object batch capacity isolation, immutable identity and cleanup without S3 or PostgreSQL."""

from __future__ import annotations

import asyncio

from inkcre_extension_registry.service.errors import RegistryConflictError
from inkcre_extension_registry.service.storage import Artifact, ArtifactStore, StoredObject


class ControlledStore(ArtifactStore):
    """The existing head/put seam provides observable operations, without a network client."""

    def __init__(self) -> None:
        self.started: asyncio.Queue[str] = asyncio.Queue()
        self.release = asyncio.Event()
        self.active = 0
        self.peak = 0
        self.objects: dict[str, bytes] = {}

    async def head(self, key: str) -> StoredObject | None:
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.started.put_nowait(key)
        try:
            if key.startswith("held/"):
                await self.release.wait()
            return StoredObject(len(self.objects[key])) if key in self.objects else None
        finally:
            self.active -= 1

    async def put(self, key: str, content: bytes, *, content_type: str) -> None:
        self.objects[key] = content


def artifacts(prefix: str, count: int):
    return [Artifact(f"{prefix}/{index}", b"value", "text/plain") for index in range(count)]


async def main() -> None:
    store = ControlledStore()
    mf = store.batch(concurrency=4)
    documentation = store.batch(concurrency=4)
    uploading = asyncio.create_task(mf.ensure_many(artifacts("held/mf", 8)))
    async with asyncio.timeout(5):
        for _ in range(4):
            assert (await store.started.get()).startswith("held/mf/")
        # Saturating MF does not occupy documentation's own budget or Python's
        # direct ensure path. MF publication shares MF's budget across requests.
        docs = asyncio.create_task(documentation.ensure_many(artifacts("held/docs", 8)))
        for _ in range(4):
            assert (await store.started.get()).startswith("held/docs/")
        await store.ensure("python/wheel", b"wheel", "application/octet-stream")
        checking = asyncio.create_task(mf.available(["mf/existing"]))
        await asyncio.sleep(0)
        assert not checking.done()
        assert store.active == 8 and store.peak == 9
        store.release.set()
        await asyncio.gather(uploading, docs)
        assert not await checking
    assert store.active == 0
    assert len([key for key in store.objects if key.startswith("held/")]) == 16
    assert await mf.available(["held/mf/0", "held/mf/1"])
    await store.ensure("python/wheel", b"wheel", "application/octet-stream")
    try:
        await mf.ensure_many([Artifact("python/wheel", b"wrong size", "application/octet-stream")])
    except RegistryConflictError:
        pass
    else:
        raise AssertionError("immutable object conflict lost its original domain type")
    assert store.objects["python/wheel"] == b"wheel"

    # A batch error must cancel and finish every sibling before it returns, and
    # releasing the failed group's capacity must make a later request usable.
    store.release.clear()
    store.objects["wrong"] = b"wrong size"
    try:
        await mf.ensure_many([*artifacts("held/failure", 3), Artifact("wrong", b"x", "text/plain")])
    except RegistryConflictError:
        pass
    else:
        raise AssertionError("batch conflict was suppressed")
    assert store.active == 0
    assert await mf.available(["wrong"])
    canceled = asyncio.create_task(mf.ensure_many(artifacts("held/cancel", 8)))
    async with asyncio.timeout(5):
        while store.active != 4:
            await asyncio.sleep(0)
    canceled.cancel()
    try:
        await canceled
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("batch swallowed caller cancellation")
    assert store.active == 0
    assert await mf.available(["wrong"])
    print("Independent MF/docs capacity, direct Python staging, batch failure/cancellation passed.")


if __name__ == "__main__":
    asyncio.run(main())
