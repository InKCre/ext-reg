"""Task-scoped SDK public-boundary experiment, independent of a Core database."""

import asyncio
import sys
import types
from typing import ClassVar
from unittest.mock import patch

import fastapi
import httpx
import pydantic


class PeerRegistry:
    entries: ClassVar[dict] = {}

    @classmethod
    def register_inbound(cls, inbound):
        if inbound.capability in cls.entries:
            raise RuntimeError("duplicate inbound")
        cls.entries[inbound.capability] = inbound
        return True

    @classmethod
    def unregister_inbound(cls, capability):
        cls.entries.pop(capability, None)


class SourceCatalog:
    entered = None
    resume = None

    @classmethod
    def sync_source_types(cls):
        pass

    @classmethod
    async def sync_source_types_async(cls):
        if cls.entered is not None:
            cls.entered.set()
            await cls.resume.wait()


class Config(pydantic.BaseModel):
    label: str = "original"


class State(pydantic.BaseModel):
    count: int = 0


class HostRecord:
    name = "inkcre/probe"

    def __init__(self):
        self.config = {"label": "original"}
        self.state = {"count": 0}
        self.lock = asyncio.Lock()
        self.entered = None
        self.resume = None
        self.fail_schema = False

    def update_config_schema(self, schema):
        self.schema = schema
        return self

    async def update_config_schema_async(self, schema):
        if self.entered is not None:
            self.entered.set()
            await self.resume.wait()
        if self.fail_schema:
            raise ValueError("schema write failed")
        return self.update_config_schema(schema)

    async def update_config_async(self, value):
        async with self.lock:
            self.config = value
        return self

    async def read_state_async(self):
        async with self.lock:
            return dict(self.state)

    async def mutate_state_async(self, transform):
        async with self.lock:
            self.state = transform(self.state)

    async def mutate_config_and_state_async(self, transform):
        async with self.lock:
            self.config, self.state = transform(self.config, self.state)


def host_modules():
    modules = {}
    for name in ("app", "app.business", "app.business.source", "app.schemas"):
        modules[name] = types.ModuleType(name)
        modules[name].__path__ = []
    for name, attributes in {
        "app.business.peer": {"PeerManager": PeerRegistry},
        "app.business.source.main": {"SourceManager": SourceCatalog},
        "app.schemas.peer": {"CapabilityID": str},
    }.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module
    return modules


async def exercise():
    from inkcre_extension_runtime_core_py import ExtensionBase, ExtensionLifecycleError

    class Probe(ExtensionBase, ext_id="probe", config_cls=Config, state_cls=State):
        @classmethod
        def api_dependencies(cls):
            return []

        @classmethod
        def _register_apis(cls, router):
            @router.get("/callback")
            def callback():
                return {"ok": True}

        @classmethod
        def peer_inbounds(cls):
            return (types.SimpleNamespace(capability="probe.read"),)

    record = HostRecord()
    Probe.bind(record)
    app = fastapi.FastAPI()

    @app.get("/unrelated")
    def unrelated():
        return {"retained": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:

        async def verify_withdrawn():
            assert not Probe.runtime_active()
            assert (await client.get("/probe/callback")).status_code == 404
            assert (await client.get("/unrelated")).status_code == 200
            assert "probe.read" not in PeerRegistry.entries

        updated = await Probe.update_config_async({"label": "changed"})
        assert updated.label == record.config["label"] == "changed"
        assert (await Probe.get_state_async()).count == 0
        state = State(count=3)
        assert await Probe.mutate_state_async(lambda current: state) is state
        assert (await Probe.get_state_async()).count == 3
        config = Config(label="atomic")
        result = await Probe.mutate_config_and_state_async(lambda before, current: (config, state))
        assert result[0] is config and result[1] is state
        assert record.config == {"label": "atomic"} and record.state == {"count": 3}

        # Exercise cancellation at both externally awaited startup boundaries.
        for owner in (SourceCatalog, record):
            owner.entered, owner.resume = asyncio.Event(), asyncio.Event()
            starting = asyncio.create_task(Probe.on_start_async(app))
            entered = asyncio.create_task(owner.entered.wait())
            try:
                async with asyncio.timeout(5):
                    done, _ = await asyncio.wait(
                        (starting, entered), return_when=asyncio.FIRST_COMPLETED
                    )
                if starting in done:
                    await starting
                    raise AssertionError("startup did not await the blocked Host capability")
            finally:
                entered.cancel()
            assert not Probe.runtime_active()
            try:
                await Probe.on_start_async(app)
            except ExtensionLifecycleError:
                pass
            else:
                raise AssertionError("overlapping startup was accepted")
            starting.cancel()
            try:
                await starting
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError("startup swallowed cancellation")
            owner.entered = owner.resume = None
            await verify_withdrawn()

        record.fail_schema = True
        try:
            await Probe.on_start_async(app)
        except ValueError as error:
            assert str(error) == "schema write failed"
        else:
            raise AssertionError("startup swallowed a persistence failure")
        await verify_withdrawn()
        record.fail_schema = False

        await Probe.on_start_async(app)
        assert Probe.runtime_active()
        assert (await client.get("/probe/callback")).json() == {"ok": True}
        Probe.unpublish()
        Probe.release_runtime()
        await verify_withdrawn()
        # Existing synchronous Hosts still use the same publication/withdrawal mechanism.
        Probe.on_start(app)
        assert Probe.runtime_active()
        Probe.unpublish()
        Probe.release_runtime()
        await verify_withdrawn()
        Probe.unbind()
    print("SDK async persistence, cancellation/rollback, restart and sync compatibility: passed")


if __name__ == "__main__":
    with patch.dict(sys.modules, host_modules()):
        asyncio.run(exercise())
