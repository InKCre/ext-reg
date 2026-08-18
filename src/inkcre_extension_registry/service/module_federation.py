"""Registry adapter for Toolkit-owned Module Federation validation."""

from inkcre_extension_toolkit.module_federation import (
    ModuleFederationSnapshot,
    ModuleFederationValidationError,
    inspect_module_federation_snapshot,
    validate_relative_asset_path,
)

__all__ = [
    "ModuleFederationSnapshot",
    "ModuleFederationValidationError",
    "inspect_module_federation_snapshot",
    "validate_relative_asset_path",
]
