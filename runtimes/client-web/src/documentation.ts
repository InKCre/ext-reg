import type { DocumentationRecord } from './generated/types.gen'
import { zReleaseDocumentation, zNativeReleaseDocumentation } from './generated/zod.gen'
import { RegistryDocumentationError } from './errors'
import { assertCoordinate, registryOrigin } from './registry'

export type ExtensionDocumentationLink = Pick<DocumentationRecord, 'scope' | 'entry_url'>

/** Discover exact installed Release links without loading documentation or checking Host compatibility.
 * A 404 returns null; a readable Release without documentation returns an empty array.
 */
export async function getExtensionDocumentation(
  origin: string,
  name: string,
  version: string,
  distribution?: 'python' | 'module_federation',
): Promise<ExtensionDocumentationLink[] | null> {
  assertCoordinate(name, version)
  const [namespace, localName] = name.split('/') as [string, string]
  const path = distribution
    ? `/v2/extensions/${encodeURIComponent(namespace)}/${encodeURIComponent(localName)}/distributions/${distribution}/releases/${encodeURIComponent(version)}/documentation`
    : `/v1/extensions/${encodeURIComponent(namespace)}/${encodeURIComponent(localName)}/releases/${encodeURIComponent(version)}/documentation`
  let response: Response
  try {
    response = await fetch(new URL(path, registryOrigin(origin)), {
      credentials: 'omit',
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new RegistryDocumentationError(
      'Extension documentation request could not reach the Registry.',
    )
  }
  if (response.status === 404) return null
  if (!response.ok)
    throw new RegistryDocumentationError(
      `Extension documentation request failed with HTTP ${response.status}.`,
    )
  let data: unknown
  try {
    data = await response.json()
  } catch {
    throw new RegistryDocumentationError('Registry returned invalid exact Release documentation.')
  }
  const parsed = distribution
    ? zNativeReleaseDocumentation.safeParse(data)
    : zReleaseDocumentation.safeParse(data)
  if (
    !parsed.success ||
    parsed.data.name !== name ||
    parsed.data.version !== version ||
    (distribution !== undefined &&
      (!('distribution' in parsed.data) || parsed.data.distribution !== distribution)) ||
    !['published', 'yanked'].includes(parsed.data.state)
  ) {
    throw new RegistryDocumentationError('Registry returned invalid exact Release documentation.')
  }
  return parsed.data.sets.map(({ scope, entry_url }) => {
    let url: URL
    try {
      url = new URL(entry_url)
    } catch {
      throw new RegistryDocumentationError('Registry returned an invalid documentation URL.')
    }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
      throw new RegistryDocumentationError('Registry returned an unsafe documentation URL.')
    }
    return { scope, entry_url: url.href }
  })
}
