"""Core-specific Extension orchestration with local-first enable."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import typing
from dataclasses import dataclass

from .base import ExtensionBase
from .contracts import PythonReleaseDescriptor, ReleaseState
from .distribution import AcquiredDistribution, PipDistributionConsumer
from .errors import (
    ExtensionCompatibilityError,
    ExtensionNotInstalledError,
    ExtensionRestartRequiredError,
    ExtensionStateConflictError,
    translate_host_model_error,
)
from .modules import DistributionModules
from .release import RegistryReleaseClient, require_python_association, validate_coordinate


@dataclass
class RunningExtension:
    model: typing.Any
    association: PythonReleaseDescriptor | None
    acquired: AcquiredDistribution
    extension_class: type[ExtensionBase]
    modules: DistributionModules
    claim: typing.Any


def _host_model() -> type[typing.Any]:
    return importlib.import_module("app.schemas.extension").ExtensionModel


def _host_version() -> str:
    return typing.cast(str, importlib.import_module("app.version").CORE_VERSION)


def _registry_origin() -> str:
    config = importlib.import_module("app.business.extension.config")
    return typing.cast(str, config.resolve_extension_registry_origin())


class ExtensionManager:
    def __init__(self) -> None:
        self.running: dict[str, RunningExtension] = {}
        self.fastapi_app: typing.Any = None
        self._loaded_versions: dict[str, str] = {}

    def list(self) -> tuple[typing.Any, ...]:
        return tuple(_host_model().list())

    def get(self, name: str) -> typing.Any:
        validate_coordinate(name)
        try:
            model = _host_model().get(name)
        except Exception as error:
            translate_host_model_error(error)
        if model is None:
            raise ExtensionNotInstalledError(f"{name} is not installed")
        return model

    def install(self, name: str, version: str) -> typing.Any:
        validate_coordinate(name, version)
        try:
            current = _host_model().get(name)
        except Exception as error:
            translate_host_model_error(error)
        if current is not None and current.version == version:
            return current
        loaded = self._loaded_versions.get(name)
        if loaded is not None and loaded != version:
            raise ExtensionRestartRequiredError(
                "A different Extension version was already imported"
            )
        origin = _registry_origin()
        release = RegistryReleaseClient(origin).get(name, version)
        if release.state is not ReleaseState.published:
            raise ExtensionCompatibilityError("Release is not published")
        require_python_association(release, _host_version())
        try:
            return _host_model().install(name, version, release.nickname)
        except Exception as error:
            translate_host_model_error(error)

    def uninstall(self, name: str) -> None:
        if name in self.running:
            raise ExtensionStateConflictError("Cannot uninstall a running Extension")
        try:
            self.get(name).uninstall()
        except Exception as error:
            translate_host_model_error(error)

    def update_config(self, name: str, config: dict[str, typing.Any]) -> typing.Any:
        running = self.running.get(name)
        if running is None:
            return self.get(name).update_config(config)
        running.extension_class.update_config(config)
        return self.get(name)

    async def enable(self, name: str, peer: typing.Any = None) -> typing.Any:
        model = self.get(name)
        current = self.running.get(name)
        if current is not None:
            if current.model.version != model.version:
                raise ExtensionRestartRequiredError("A different Extension version is running")
            return current.model
        host_version = _host_version()
        acquired = await asyncio.to_thread(
            AcquiredDistribution.discover, name, model.version, host_version
        )
        association = None
        if acquired is None:
            origin = _registry_origin()
            release = RegistryReleaseClient(origin).get(name, model.version)
            association = require_python_association(release, host_version)
            acquired = await asyncio.to_thread(
                PipDistributionConsumer(origin).acquire,
                release,
                association,
                host_version,
            )
        running = await self._start(model, association, acquired)
        try:
            running.model = running.model.enable_peer(peer)
        except Exception as error:
            await self._force_stop(running)
            translate_host_model_error(error)
        return running.model

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
                with contextlib.suppress(Exception):
                    await extension_class.on_close()
                extension_class.unbind()
            modules.abort()
            claim.release()
            raise
        running = RunningExtension(model, association, acquired, extension_class, modules, claim)
        self.running[model.name] = running
        self._loaded_versions[model.name] = model.version
        return running

    async def disable(self, name: str, peer: typing.Any = None) -> typing.Any:
        running = self.running.get(name)
        model = self.get(name)
        if running is not None:
            await self._stop(running)
        try:
            return model.disable_peer(peer)
        except Exception as error:
            if running is not None:
                await self._start(model, running.association, running.acquired)
            translate_host_model_error(error)

    async def _stop(self, running: RunningExtension) -> None:
        await running.extension_class.on_close()
        running.extension_class.unpublish()
        running.extension_class.unbind()
        running.modules.unload()
        running.extension_class.release_runtime()
        running.claim.release()
        self.running.pop(running.model.name, None)

    async def _force_stop(self, running: RunningExtension) -> None:
        with contextlib.suppress(Exception):
            await running.extension_class.on_close()
        with contextlib.suppress(Exception):
            running.extension_class.unpublish()
        running.extension_class.unbind()
        running.modules.abort()
        running.extension_class.release_runtime()
        running.claim.release()
        self.running.pop(running.model.name, None)

    async def startup(self, app: typing.Any, peer: typing.Any = None) -> None:
        self.fastapi_app = app
        for model in self.list():
            if peer in model.enabled:
                await self.enable(model.name, peer)

    async def shutdown(self) -> None:
        for running in tuple(self.running.values())[::-1]:
            await self._force_stop(running)
