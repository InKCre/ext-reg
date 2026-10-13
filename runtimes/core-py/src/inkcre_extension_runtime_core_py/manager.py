"""Core-specific Extension orchestration with local-first enable."""

from __future__ import annotations

import asyncio
import logging
import typing
from dataclasses import dataclass

from .base import ExtensionBase
from .contracts import PythonReleaseDescriptor, ReleaseState
from .distribution import AcquiredDistribution
from .errors import (
    ExtensionCompatibilityError,
    ExtensionEnvironmentApplicationRequiredError,
    ExtensionNotInstalledError,
    ExtensionStateConflictError,
)
from .modules import DistributionModules
from .release import RegistryReleaseClient, require_python_association, validate_coordinate

logger = logging.getLogger(__name__)


@dataclass
class RunningExtension:
    model: typing.Any
    association: PythonReleaseDescriptor | None
    acquired: AcquiredDistribution
    extension_class: type[ExtensionBase]
    claim: typing.Any


class ParticipationStore(typing.Protocol):
    def list_participations(self, peer_id: str) -> typing.Iterable[typing.Any]: ...
    def get_participation(self, peer_id: str, name: str) -> typing.Any: ...
    def select_participation(
        self, peer_id: str, name: str, distribution: str, version: str
    ) -> typing.Any: ...
    def set_participation_enabled(self, peer_id: str, name: str, enabled: bool) -> typing.Any: ...
    def remove_participation(self, peer_id: str, name: str) -> None: ...


class ExtensionManager:
    def __init__(
        self,
        store: ParticipationStore,
        models: typing.Any,
        *,
        peer_id: str,
        registry_origin: str,
        host_version: str,
    ) -> None:
        self.store = store
        self.models = models
        self.peer_id = peer_id
        self.registry_origin = registry_origin
        self.host_version = host_version
        self.running: dict[str, RunningExtension] = {}
        self.fastapi_app: typing.Any = None

    def list(self) -> tuple[typing.Any, ...]:
        return tuple(self.models.list())

    def get(self, name: str) -> typing.Any:
        validate_coordinate(name)
        model = self.models.get(name)
        if model is None:
            raise ExtensionNotInstalledError(f"{name} is not installed")
        return model

    def install(self, name: str, version: str) -> typing.Any:
        validate_coordinate(name, version)
        release = RegistryReleaseClient(self.registry_origin).get(name, version)
        if release.state is not ReleaseState.published:
            raise ExtensionCompatibilityError("Release is not published")
        require_python_association(release, self.host_version)
        return self.store.select_participation(self.peer_id, name, "python", version)

    def uninstall(self, name: str) -> None:
        if name in self.running:
            raise ExtensionStateConflictError("Cannot remove a running participation")
        self.store.remove_participation(self.peer_id, name)

    def update_config(self, name: str, config: dict[str, typing.Any]) -> typing.Any:
        running = self.running.get(name)
        if running is None:
            return self.get(name).update_config(config)
        running.extension_class.update_config(config)
        return self.get(name)

    async def enable(self, name: str, peer: typing.Any = None) -> typing.Any:
        model = self.get(name)
        selection = self.store.get_participation(self.peer_id, name)
        if selection is None:
            raise ExtensionNotInstalledError(f"{name} is not selected for this Peer")
        if selection.distribution is None:
            release = RegistryReleaseClient(self.registry_origin).get(name, selection.version)
            require_python_association(release, self.host_version)
            selection = self.store.select_participation(
                self.peer_id, name, "python", selection.version
            )
        if selection.distribution != "python":
            raise ExtensionCompatibilityError("Selected distribution cannot run in this Peer")
        current = self.running.get(name)
        if current is not None:
            if current.acquired.record.version != selection.version:
                raise ExtensionStateConflictError("A different Extension version is running")
            return selection
        acquired = await asyncio.to_thread(
            AcquiredDistribution.discover, name, selection.version, self.host_version
        )
        if acquired is None:
            raise ExtensionEnvironmentApplicationRequiredError(
                "Applying this Python distribution requires a stopped Peer and a new process"
            )
        running = await self._start(model, None, acquired)
        try:
            return self.store.set_participation_enabled(self.peer_id, name, True)
        except Exception:
            await self._force_stop(running)
            raise

    async def _start(
        self,
        model: typing.Any,
        association: PythonReleaseDescriptor | None,
        acquired: AcquiredDistribution,
    ) -> RunningExtension:
        from .publication import ExtensionRuntimeClaim, ExtensionRuntimeClaimConflictError

        try:
            claim = ExtensionRuntimeClaim.acquire(acquired.record.python.entry_point.name)
        except ExtensionRuntimeClaimConflictError as error:
            raise ExtensionStateConflictError(str(error)) from error
        modules = DistributionModules(acquired)
        extension_class: type[ExtensionBase] | None = None
        try:
            extension_class = modules.load(ExtensionBase)
            if extension_class.__extid__ != acquired.record.python.entry_point.name:
                raise ExtensionCompatibilityError(
                    "Extension identity differs from installed entry point"
                )
            extension_class.bind(model)
            extension_class.on_start(self.fastapi_app)
            modules.assert_origins()
        except Exception:
            if extension_class is not None:
                try:
                    await extension_class.on_close()
                except Exception:
                    logger.exception(
                        "Extension %s on_close failed after startup failure", model.name
                    )
                cleanup = (
                    ("unpublish", extension_class.unpublish),
                    ("unbind", extension_class.unbind),
                    ("runtime release", extension_class.release_runtime),
                )
                for operation, action in cleanup:
                    try:
                        action()
                    except Exception:
                        logger.exception(
                            "Extension %s %s failed after startup failure",
                            model.name,
                            operation,
                        )
            claim.release()
            raise
        running = RunningExtension(model, association, acquired, extension_class, claim)
        self.running[model.name] = running
        return running

    async def disable(self, name: str, peer: typing.Any = None) -> typing.Any:
        running = self.running.get(name)
        model = self.get(name)
        if running is not None:
            await self._stop(running)
        try:
            return self.store.set_participation_enabled(self.peer_id, name, False)
        except Exception:
            if running is not None:
                await self._start(model, running.association, running.acquired)
            raise

    async def _stop(self, running: RunningExtension) -> None:
        await running.extension_class.on_close()
        running.extension_class.unpublish()
        running.extension_class.unbind()
        running.extension_class.release_runtime()
        running.claim.release()
        self.running.pop(running.model.name, None)

    async def _force_stop(self, running: RunningExtension) -> None:
        try:
            await running.extension_class.on_close()
        except Exception:
            logger.exception("Extension %s on_close failed during cleanup", running.model.name)
        cleanup = (
            ("unpublish", running.extension_class.unpublish),
            ("unbind", running.extension_class.unbind),
            ("runtime release", running.extension_class.release_runtime),
            ("claim release", running.claim.release),
        )
        for operation, action in cleanup:
            try:
                action()
            except Exception:
                logger.exception(
                    "Extension %s %s failed during cleanup", running.model.name, operation
                )
        self.running.pop(running.model.name, None)

    async def startup(self, app: typing.Any, peer: typing.Any = None) -> None:
        self.fastapi_app = app
        for selection in self.store.list_participations(self.peer_id):
            if selection.enabled:
                try:
                    await self.enable(selection.name, peer)
                except Exception:
                    logger.exception("Extension %s failed to start", selection.name)

    async def shutdown(self) -> None:
        for running in tuple(self.running.values())[::-1]:
            await self._force_stop(running)
