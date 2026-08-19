"""Entry-point loading with reversible module ownership."""

from __future__ import annotations

import contextlib
import importlib
import sys
import typing
from pathlib import Path

from .distribution import AcquiredDistribution
from .errors import ExtensionEntryPointError


class DistributionModules:
    def __init__(self, acquired: AcquiredDistribution) -> None:
        self.acquired = acquired
        module = acquired.entry_point.value.partition(":")[0]
        parts = module.split(".")
        if len(parts) < 2 or parts[0] != "extensions" or parts[1] != acquired.entry_point.name:
            raise ExtensionEntryPointError(
                "Core Extension entry point must live in its declared extensions.<name> package"
            )
        self.package_name = ".".join(parts[:2])
        self._previous: dict[str, typing.Any] = {}
        self._active = False

    def _module_names(self) -> tuple[str, ...]:
        prefix = self.package_name + "."
        return tuple(
            name for name in sys.modules if name == self.package_name or name.startswith(prefix)
        )

    def load(self, base: type[typing.Any]) -> type[typing.Any]:
        if self._active:
            raise ExtensionEntryPointError("Extension Distribution is already loaded")
        self._previous = {name: sys.modules[name] for name in self._module_names()}
        for name in self._previous:
            sys.modules.pop(name, None)
        importlib.invalidate_caches()
        try:
            loaded = self.acquired.entry_point.load()
        except Exception as error:
            self.abort()
            raise ExtensionEntryPointError("Extension entry point could not be loaded") from error
        self._active = True
        if not isinstance(loaded, type) or not issubclass(loaded, base):
            self.abort()
            raise ExtensionEntryPointError("Extension entry point is not an ExtensionBase subclass")
        self.assert_origins()
        return loaded

    def assert_origins(self) -> None:
        files = {
            Path(str(self.acquired.distribution.locate_file(file))).resolve()
            for file in (self.acquired.distribution.files or ())
        }
        names = self._module_names()
        if self.package_name not in names:
            raise ExtensionEntryPointError("Extension entry-point package was not loaded")
        for module_name in names:
            module_file = getattr(sys.modules[module_name], "__file__", None)
            if module_file is None or Path(module_file).resolve() not in files:
                self.abort()
                raise ExtensionEntryPointError(
                    "Extension imported a module outside its Distribution ownership"
                )

    def unload(self) -> None:
        if self._active:
            self.assert_origins()
        self.abort()

    def abort(self) -> None:
        with contextlib.suppress(Exception):
            for name in self._module_names():
                sys.modules.pop(name, None)
            sys.modules.update(self._previous)
            importlib.invalidate_caches()
            self._active = False
