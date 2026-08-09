import {
  isTargetDigest,
  type Condition,
  type Release,
  type ReleaseState,
  type Target,
} from './contracts'

export type FetchImplementation = (input: string | URL, init?: RequestInit) => Promise<Response>

export class RegistryClientError extends Error {
  readonly status: number | undefined

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'RegistryClientError'
    this.status = status
  }
}

export class RegistryClient {
  readonly #origin: string
  readonly #fetch: FetchImplementation

  constructor(origin: string, fetchImplementation: FetchImplementation = globalThis.fetch) {
    const normalizedOrigin = origin.replace(/\/+$/, '')
    if (normalizedOrigin.length === 0) {
      throw new TypeError('Registry origin must not be empty')
    }

    this.#origin = normalizedOrigin
    this.#fetch = fetchImplementation
  }

  async getPublishedRelease(namespace: string, name: string, version: string): Promise<Release> {
    const url = this.#url(
      `v1/extensions/${encodeURIComponent(namespace)}/${encodeURIComponent(name)}/versions/${encodeURIComponent(version)}`,
    )
    const response = await this.#fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    })

    if (!response.ok) {
      const detail = (await response.text()).slice(0, 500)
      throw new RegistryClientError(
        `Registry release request failed with HTTP ${response.status}${detail ? `: ${detail}` : ''}`,
        response.status,
      )
    }

    const release = parseRelease(await response.json())
    if (release.namespace !== namespace || release.name !== name || release.version !== version) {
      throw new RegistryClientError('Registry returned a different release coordinate')
    }
    if (release.state !== 'published') {
      throw new RegistryClientError(`Registry release is not published (state: ${release.state})`)
    }

    return release
  }

  artifactManifestUrl(targetDigest: string): string {
    assertTargetDigest(targetDigest)
    return this.#url(`v1/artifacts/${targetDigest}/manifest`)
  }

  artifactFileUrl(targetDigest: string, relativePath: string): string {
    assertTargetDigest(targetDigest)
    const encodedPath = encodeArtifactPath(relativePath)
    return this.#url(`v1/artifacts/${targetDigest}/files/${encodedPath}`)
  }

  #url(path: string): string {
    return `${this.#origin}/${path}`
  }
}

function assertTargetDigest(value: string): void {
  if (!isTargetDigest(value)) {
    throw new TypeError('Target digest must match sha256:<64 lowercase hex>')
  }
}

function encodeArtifactPath(relativePath: string): string {
  if (relativePath.length === 0 || relativePath.startsWith('/') || relativePath.includes('\\')) {
    throw new TypeError('Artifact path must be a non-empty safe relative path')
  }

  const segments = relativePath.split('/')
  if (segments.some((segment) => segment.length === 0 || segment === '.' || segment === '..')) {
    throw new TypeError('Artifact path must be normalized and traversal-free')
  }

  return segments.map(encodeURIComponent).join('/')
}

function parseRelease(value: unknown): Release {
  const object = requireRecord(value, 'release')
  const state = requireString(object.state, 'release.state')
  if (!isReleaseState(state)) {
    throw new RegistryClientError(`Registry returned unsupported release state: ${state}`)
  }
  if (!Array.isArray(object.targets)) {
    throw new RegistryClientError('Registry returned invalid release.targets')
  }

  return {
    namespace: requireString(object.namespace, 'release.namespace'),
    name: requireString(object.name, 'release.name'),
    version: requireString(object.version, 'release.version'),
    state,
    targets: object.targets.map(parseTarget),
  }
}

function parseTarget(value: unknown): Target {
  const object = requireRecord(value, 'target')
  if (!Array.isArray(object.conditions)) {
    throw new RegistryClientError('Registry returned invalid target.conditions')
  }

  const targetDigest = requireString(object.target_digest, 'target.target_digest')
  if (!isTargetDigest(targetDigest)) {
    throw new RegistryClientError('Registry returned invalid target.target_digest')
  }

  return {
    target_key: requireString(object.target_key, 'target.target_key'),
    target_digest: targetDigest,
    artifact_format: requireString(object.artifact_format, 'target.artifact_format'),
    entrypoint: requireString(object.entrypoint, 'target.entrypoint'),
    conditions: object.conditions.map(parseCondition),
    source_repository: optionalNullableString(object.source_repository, 'target.source_repository'),
    source_revision: optionalNullableString(object.source_revision, 'target.source_revision'),
    build_id: optionalNullableString(object.build_id, 'target.build_id'),
  }
}

function parseCondition(value: unknown): Condition {
  const object = requireRecord(value, 'condition')
  const operator = requireString(object.operator, 'condition.operator')
  if (operator !== 'equals' && operator !== 'semver') {
    throw new RegistryClientError(`Registry returned unsupported condition operator: ${operator}`)
  }

  return {
    key: requireString(object.key, 'condition.key'),
    operator,
    value: requireString(object.value, 'condition.value'),
  }
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new RegistryClientError(`Registry returned invalid ${label}`)
  }
  return value as Record<string, unknown>
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== 'string') {
    throw new RegistryClientError(`Registry returned invalid ${label}`)
  }
  return value
}

function optionalNullableString(value: unknown, label: string): string | null | undefined {
  if (value === undefined || value === null || typeof value === 'string') {
    return value
  }
  throw new RegistryClientError(`Registry returned invalid ${label}`)
}

function isReleaseState(value: string): value is ReleaseState {
  return value === 'preparing' || value === 'published' || value === 'yanked' || value === 'blocked'
}
