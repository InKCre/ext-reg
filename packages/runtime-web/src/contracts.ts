export const CONDITION_KEYS = [
  'inkcre.integration',
  'inkcre.extension-api',
  'module-federation.runtime',
  'module-federation.share-scope',
  'shared.vue',
  'shared.@inkcre/core',
  'web.ecmascript',
  'python',
] as const

export type ConditionKey = (typeof CONDITION_KEYS)[number]
export type ConditionOperator = 'equals' | 'semver'

/** One mandatory target predicate evaluated against a Platform Profile. */
export interface Condition {
  readonly key: string
  readonly operator: ConditionOperator
  readonly value: string
}

/** Exact capability values reported by a consumer adapter. */
export type PlatformProfile = Readonly<Record<string, string | undefined>>

export interface Target {
  readonly target_key: string
  readonly target_digest: string
  readonly artifact_format: string
  readonly entrypoint: string
  readonly conditions: readonly Condition[]
  readonly source_repository?: string | null
  readonly source_revision?: string | null
  readonly build_id?: string | null
}

export type ReleaseState = 'preparing' | 'published' | 'yanked' | 'blocked'

export interface Release {
  readonly namespace: string
  readonly name: string
  readonly version: string
  readonly state: ReleaseState
  readonly targets: readonly Target[]
}

export const TARGET_DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/

export function isConditionKey(value: string): value is ConditionKey {
  return (CONDITION_KEYS as readonly string[]).includes(value)
}

export function isTargetDigest(value: string): boolean {
  return TARGET_DIGEST_PATTERN.test(value)
}
