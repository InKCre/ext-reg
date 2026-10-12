"""Stable Runtime error taxonomy."""

import importlib
import typing


class ExtensionRuntimeError(RuntimeError):
    """Base error for the Core Python Extension Runtime."""


class ExtensionNotInstalledError(ExtensionRuntimeError): ...


class ExtensionStateConflictError(ExtensionRuntimeError): ...


class ExtensionRegistryError(ExtensionRuntimeError): ...


class ExtensionReleaseUnavailableError(ExtensionRegistryError):
    def __init__(self, status: typing.Literal[404, 451]) -> None:
        self.status = status
        super().__init__(f"Extension Release is unavailable (HTTP {status})")


class ExtensionNativeSupportChangeError(ExtensionRuntimeError):
    def __init__(
        self,
        name: str,
        installed_version: str,
        target_version: str,
        removed_formats: tuple[str, ...],
        reason: typing.Literal["reduced", "unavailable"],
    ) -> None:
        self.name = name
        self.installed_version = installed_version
        self.target_version = target_version
        self.removed_formats = removed_formats
        self.reason = reason
        super().__init__(
            f"{name}@{target_version} removes native support: {', '.join(removed_formats)}"
            if reason == "reduced"
            else f"Cannot verify native support of installed {name}@{installed_version}"
        )


class ExtensionCompatibilityError(ExtensionRuntimeError): ...


class ExtensionAcquisitionError(ExtensionRuntimeError): ...


class ExtensionEntryPointError(ExtensionRuntimeError): ...


class ExtensionLifecycleError(ExtensionRuntimeError): ...


def translate_host_model_error(error: Exception) -> typing.NoReturn:
    """Translate the concrete Core Active Record boundary without a reverse dependency."""
    try:
        schemas = importlib.import_module("app.schemas.extension")
    except ModuleNotFoundError:
        raise error from None
    if isinstance(error, schemas.ExtensionModelNotFoundError):
        raise ExtensionNotInstalledError(str(error)) from error
    if isinstance(error, schemas.ExtensionModelConflictError):
        raise ExtensionStateConflictError(str(error)) from error
    raise error
