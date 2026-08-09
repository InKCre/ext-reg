from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from contextlib import suppress
from enum import StrEnum
from typing import Protocol


class ExtensionState(StrEnum):
    DISCOVERED = "DISCOVERED"
    LOADING = "LOADING"
    LOADED = "LOADED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    DEACTIVATING = "DEACTIVATING"
    DISPOSING = "DISPOSING"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


class ExtensionHooks(Protocol):
    def initialize(self) -> Awaitable[None] | None: ...

    def activate(self) -> Awaitable[None] | None: ...

    def deactivate(self) -> Awaitable[None] | None: ...

    def dispose(self) -> Awaitable[None] | None: ...


async def _maybe_await(value: Awaitable[None] | None) -> None:
    if inspect.isawaitable(value):
        await value


class ExtensionLifecycle[HooksT: ExtensionHooks]:
    """Small host-independent executor for the stable Extension hook contract."""

    def __init__(self, loader: Callable[[], Awaitable[HooksT] | HooksT]) -> None:
        self._loader = loader
        self.hooks: HooksT | None = None
        self.state = ExtensionState.DISCOVERED
        self.error: Exception | None = None

    async def enable(self) -> None:
        if self.state not in {ExtensionState.DISCOVERED, ExtensionState.UNLOADED}:
            raise RuntimeError(f"cannot enable extension from {self.state}")
        activation_started = False
        try:
            self.state = ExtensionState.LOADING
            loaded = self._loader()
            hooks = await loaded if inspect.isawaitable(loaded) else loaded
            self.hooks = hooks
            self.state = ExtensionState.LOADED
            self.state = ExtensionState.INITIALIZING
            await _maybe_await(hooks.initialize())
            self.state = ExtensionState.READY
            self.state = ExtensionState.ACTIVATING
            activation_started = True
            await _maybe_await(hooks.activate())
            self.state = ExtensionState.ACTIVE
            self.error = None
        except Exception as error:
            self.error = error
            if self.hooks is not None:
                if activation_started:
                    with suppress(Exception):
                        await _maybe_await(self.hooks.deactivate())
                with suppress(Exception):
                    await _maybe_await(self.hooks.dispose())
            self.hooks = None
            self.state = ExtensionState.ERROR
            raise

    async def disable(self) -> None:
        if self.state != ExtensionState.ACTIVE or self.hooks is None:
            raise RuntimeError(f"cannot disable extension from {self.state}")
        failures: list[Exception] = []
        hooks = self.hooks
        self.state = ExtensionState.DEACTIVATING
        try:
            await _maybe_await(hooks.deactivate())
        except Exception as error:
            failures.append(error)
        self.state = ExtensionState.DISPOSING
        try:
            await _maybe_await(hooks.dispose())
        except Exception as error:
            failures.append(error)
        if not failures:
            self.hooks = None
            self.state = ExtensionState.UNLOADED
            self.error = None
            return
        self.error = failures[0]
        self.state = ExtensionState.ERROR
        if len(failures) == 1:
            raise failures[0]
        raise ExceptionGroup("extension disable failed", failures)
