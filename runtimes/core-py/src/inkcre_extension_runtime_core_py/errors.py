"""Stable Runtime error taxonomy."""

import importlib
import typing


class ExtensionRuntimeError(RuntimeError):
    """Base error for the Core Python Extension Runtime."""


class ExtensionNotInstalledError(ExtensionRuntimeError): ...


class ExtensionStateConflictError(ExtensionRuntimeError): ...


class ExtensionRegistryError(ExtensionRuntimeError): ...


class ExtensionCompatibilityError(ExtensionRuntimeError): ...


class ExtensionAcquisitionError(ExtensionRuntimeError): ...


class ExtensionEntryPointError(ExtensionRuntimeError): ...


class ExtensionLifecycleError(ExtensionRuntimeError): ...


class ExtensionRestartRequiredError(ExtensionStateConflictError): ...


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
