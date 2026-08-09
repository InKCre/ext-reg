from __future__ import annotations

from semantic_version import NpmSpec, Version

from .models import PlatformProfile, TargetRecord


def target_matches(target: TargetRecord, profile: PlatformProfile) -> bool:
    """Evaluate a target's mandatory conjunction against one platform profile."""

    for condition in target.conditions:
        actual = profile.get(condition.key)
        if actual is None:
            return False
        if condition.operator == "equals":
            if actual != condition.value:
                return False
            continue
        if condition.operator == "semver":
            try:
                if not NpmSpec(condition.value).match(Version(actual)):
                    return False
            except ValueError:
                return False
            continue
        return False
    return True


def select_compatible_target(
    targets: tuple[TargetRecord, ...] | list[TargetRecord],
    profile: PlatformProfile,
) -> TargetRecord | None:
    """Return the stable target-key-first candidate selected by the adapter."""

    compatible = sorted(
        (target for target in targets if target_matches(target, profile)),
        key=lambda target: target.target_key,
    )
    return compatible[0] if compatible else None
