"""Native support preservation for exact deployment version changes."""

from collections.abc import Collection
from typing import Literal

from .errors import ExtensionNativeSupportChangeError, ExtensionStateConflictError

NativeDistributionFormat = Literal["python", "module_federation"]


def require_native_support_preserved(
    name: str,
    installed_version: str,
    target_version: str,
    previous_formats: Collection[NativeDistributionFormat] | None,
    target_formats: Collection[NativeDistributionFormat],
    *,
    expected_installed_version: str | None = None,
    allow_support_change: bool = False,
) -> None:
    if allow_support_change and expected_installed_version is None:
        raise ValueError("Support change confirmation requires expected_installed_version")
    if expected_installed_version is not None and expected_installed_version != installed_version:
        raise ExtensionStateConflictError("Installed version changed after confirmation")
    if previous_formats is None:
        if not allow_support_change:
            raise ExtensionNativeSupportChangeError(
                name, installed_version, target_version, (), "unavailable"
            )
        return
    removed = tuple(sorted(set(previous_formats) - set(target_formats)))
    if removed and not allow_support_change:
        raise ExtensionNativeSupportChangeError(
            name, installed_version, target_version, removed, "reduced"
        )
