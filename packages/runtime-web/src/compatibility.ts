import semver from 'semver'

import { isConditionKey, type Condition, type PlatformProfile, type Target } from './contracts'

export function matchesCondition(condition: Condition, profile: PlatformProfile): boolean {
  if (!isConditionKey(condition.key)) {
    return false
  }

  if (!Object.prototype.hasOwnProperty.call(profile, condition.key)) {
    return false
  }

  const actual = profile[condition.key]
  if (typeof actual !== 'string') {
    return false
  }

  switch (condition.operator) {
    case 'equals':
      return actual === condition.value
    case 'semver': {
      const exactVersion = semver.valid(actual)
      const expectedRange = semver.validRange(condition.value)
      return (
        exactVersion !== null &&
        expectedRange !== null &&
        semver.satisfies(exactVersion, expectedRange)
      )
    }
    default:
      return false
  }
}

export function isTargetCompatible(target: Target, profile: PlatformProfile): boolean {
  const declaresArtifactFormat = target.conditions.some(
    (condition) =>
      condition.key === 'inkcre.integration' &&
      condition.operator === 'equals' &&
      condition.value === target.artifact_format,
  )

  return (
    declaresArtifactFormat &&
    target.conditions.every((condition) => matchesCondition(condition, profile))
  )
}

/**
 * Selects deterministically without mutating Registry response order.
 * Publisher order is never a preference signal.
 */
export function selectCompatibleTarget(
  targets: readonly Target[],
  profile: PlatformProfile,
): Target | undefined {
  return targets
    .filter((target) => isTargetCompatible(target, profile))
    .sort((left, right) => {
      if (left.target_key < right.target_key) return -1
      if (left.target_key > right.target_key) return 1
      return 0
    })[0]
}
