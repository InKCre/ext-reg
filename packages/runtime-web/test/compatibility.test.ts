import { describe, expect, it } from 'vitest'

import {
  isTargetCompatible,
  selectCompatibleTarget,
  type PlatformProfile,
  type Target,
} from '../src'

const digest = `sha256:${'a'.repeat(64)}`

function target(target_key: string, conditions: Target['conditions']): Target {
  return {
    target_key,
    target_digest: digest,
    artifact_format: 'module-federation-esm',
    entrypoint: 'remoteEntry.js',
    conditions,
  }
}

describe('compatibility selection', () => {
  it('fails closed and selects the first compatible target by stable target key', () => {
    const profile: PlatformProfile = {
      'inkcre.integration': 'module-federation-esm',
      'inkcre.extension-api': '1.2.0',
      'shared.vue': '3.5.18',
    }
    const compatibleConditions: Target['conditions'] = [
      { key: 'inkcre.integration', operator: 'equals', value: 'module-federation-esm' },
      { key: 'inkcre.extension-api', operator: 'semver', value: '^1.0.0' },
      { key: 'shared.vue', operator: 'semver', value: '^3.5.0' },
    ]
    const candidates = [
      target('web-z', compatibleConditions),
      target('web-unknown', [
        ...compatibleConditions,
        { key: 'publisher.private-flag', operator: 'equals', value: 'yes' },
      ]),
      target('web-missing', [
        ...compatibleConditions,
        { key: 'module-federation.runtime', operator: 'semver', value: '^0.21.0' },
      ]),
      target('web-a', compatibleConditions),
    ]

    expect(isTargetCompatible(candidates[1], profile)).toBe(false)
    expect(isTargetCompatible(candidates[2], profile)).toBe(false)
    expect(isTargetCompatible(candidates[0], { ...profile, 'shared.vue': 'not-semver' })).toBe(
      false,
    )
    expect(selectCompatibleTarget(candidates, profile)?.target_key).toBe('web-a')
    expect(candidates.map((candidate) => candidate.target_key)).toEqual([
      'web-z',
      'web-unknown',
      'web-missing',
      'web-a',
    ])
  })
})
