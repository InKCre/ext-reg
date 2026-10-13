import { prerelease, rcompare, satisfies, valid as validSemVer, validRange } from 'semver'
import type {
  ExtensionRecord,
  ExtensionSummary,
  ModuleFederationDistribution,
  ReleaseRecord,
} from './generated/types.gen'
import {
  zExtensionRecord,
  zListExtensionsV1ExtensionsGetResponse,
  zReleaseRecord,
} from './generated/zod.gen'
import { HostSdkCompatibilityError, RegistryReleaseError } from './errors'

const EXTENSION_NAME =
  /^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\/[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$/

export interface HostSdkIdentity {
  readonly name: '@inkcre/core'
  readonly version: string
}

export interface RegistryReleaseReaderOptions {
  readonly registryOrigin: string | (() => string | Promise<string>)
  readonly fetch?: typeof globalThis.fetch
  readonly hostSdk: HostSdkIdentity
}

export type WebReleaseRecord = ReleaseRecord & {
  module_federation: ModuleFederationDistribution
}

export class RegistryReleaseReader {
  readonly #origin: () => string | Promise<string>
  readonly #fetch: typeof globalThis.fetch
  readonly #hostSdk: HostSdkIdentity

  constructor(options: RegistryReleaseReaderOptions) {
    if (validSemVer(options.hostSdk.version) !== options.hostSdk.version) {
      throw new TypeError('Web Host SDK version must be strict SemVer.')
    }
    this.#origin =
      typeof options.registryOrigin === 'function'
        ? options.registryOrigin
        : () => options.registryOrigin as string
    this.#fetch = (options.fetch ?? globalThis.fetch).bind(globalThis)
    this.#hostSdk = options.hostSdk
  }

  async list(): Promise<ExtensionSummary[]> {
    const origin = registryOrigin(await this.#origin())
    const value = await this.#getJson(new URL('/v1/extensions', origin))
    return zListExtensionsV1ExtensionsGetResponse.parse(value)
  }

  async getExtension(name: string): Promise<ExtensionRecord> {
    assertExtensionName(name)
    const origin = registryOrigin(await this.#origin())
    const [namespace, localName] = name.split('/') as [string, string]
    const value = await this.#getJson(
      new URL(
        `/v1/extensions/${encodeURIComponent(namespace)}/${encodeURIComponent(localName)}`,
        origin,
      ),
    )
    const extension = zExtensionRecord.parse(value)
    if (extension.name !== name) {
      throw new RegistryReleaseError('Registry returned a different Extension coordinate.')
    }
    return extension
  }

  async getRelease(
    name: string,
    version: string,
    requirePublished: boolean,
  ): Promise<ReleaseRecord> {
    const origin = registryOrigin(await this.#origin())
    return this.#getRelease(origin, name, version, requirePublished)
  }

  async get(name: string, version: string, requirePublished: boolean): Promise<WebReleaseRecord> {
    const origin = registryOrigin(await this.#origin())
    const release = await this.#getRelease(origin, name, version, requirePublished)
    const distribution = release.module_federation
    if (!distribution) {
      throw new HostSdkCompatibilityError(
        `Release ${name}@${version} has no Module Federation Distribution.`,
      )
    }
    this.#assertHostSdk(distribution, name, version)
    const manifest = new URL(distribution.manifest_url, origin)
    if (manifest.origin !== origin.origin) {
      throw new RegistryReleaseError(
        'Module Federation manifest must be hosted by the configured Registry.',
      )
    }
    return { ...release, module_federation: { ...distribution, manifest_url: manifest.href } }
  }

  async #getRelease(
    origin: URL,
    name: string,
    version: string,
    requirePublished: boolean,
  ): Promise<ReleaseRecord> {
    assertCoordinate(name, version)
    const [namespace, localName] = name.split('/') as [string, string]
    const url = new URL(
      `/v1/extensions/${encodeURIComponent(namespace)}/${encodeURIComponent(localName)}/releases/${encodeURIComponent(version)}`,
      origin,
    )
    const release = zReleaseRecord.parse(await this.#getJson(url))
    if (release.name !== name || release.version !== version) {
      throw new RegistryReleaseError('Registry returned a different exact Release coordinate.')
    }
    if (
      requirePublished
        ? release.state !== 'published'
        : !['published', 'yanked'].includes(release.state)
    ) {
      throw new RegistryReleaseError(
        `Release ${name}@${version} is not available in state ${release.state}.`,
      )
    }
    return release
  }

  async #getJson(url: URL): Promise<unknown> {
    const response = await this.#fetch(url, { headers: { Accept: 'application/json' } })
    if (!response.ok) {
      throw new RegistryReleaseError(
        `Extension Registry request failed with HTTP ${response.status}.`,
      )
    }
    return response.json()
  }

  #assertHostSdk(distribution: ModuleFederationDistribution, name: string, version: string): void {
    if (distribution.host_sdk !== this.#hostSdk.name) {
      throw new HostSdkCompatibilityError(
        `${name}@${version} targets ${distribution.host_sdk}, expected ${this.#hostSdk.name}.`,
      )
    }
    const range = distribution.host_sdk_version.replace(/,/g, ' ')
    if (!validRange(range) || !satisfies(this.#hostSdk.version, range)) {
      throw new HostSdkCompatibilityError(
        `Host SDK ${this.#hostSdk.version} does not satisfy ${distribution.host_sdk_version}.`,
      )
    }
  }
}

/** Validate an origin already selected by the Host's Registry origin resolver. */
export function registryOrigin(value: string): URL {
  const origin = new URL(value)
  if (
    !['http:', 'https:'].includes(origin.protocol) ||
    origin.username !== '' ||
    origin.password !== '' ||
    !['', '/'].includes(origin.pathname) ||
    origin.search !== '' ||
    origin.hash !== ''
  ) {
    throw new RegistryReleaseError('Extension Registry URL must be a bare HTTP origin.')
  }
  return origin
}

export function assertCoordinate(name: string, version: string): void {
  assertExtensionName(name)
  if (validSemVer(version) !== version || version.includes('+')) {
    throw new RegistryReleaseError(
      'Extension version must be strict SemVer without build metadata.',
    )
  }
}

export function sortPublishedReleases(releases: readonly ReleaseRecord[]): ReleaseRecord[] {
  return releases
    .filter(({ state }) => state === 'published')
    .sort((left, right) => rcompare(left.version, right.version))
}

export function preferredPublishedRelease(
  releases: readonly ReleaseRecord[],
): ReleaseRecord | null {
  const ordered = sortPublishedReleases(releases)
  return ordered.find(({ version }) => prerelease(version) === null) ?? ordered[0] ?? null
}

function assertExtensionName(name: string): void {
  if (!EXTENSION_NAME.test(name)) throw new RegistryReleaseError('Invalid Extension name.')
}
