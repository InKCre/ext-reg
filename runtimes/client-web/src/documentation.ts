import { createClient } from './generated/client'
import { getDocumentationV1ExtensionsNamespaceNameReleasesVersionDocumentationGet } from './generated/sdk.gen'
import type { DocumentationRecord } from './generated/types.gen'
import { zReleaseDocumentation } from './generated/zod.gen'
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
): Promise<ExtensionDocumentationLink[] | null> {
  assertCoordinate(name, version)
  const [namespace, localName] = name.split('/') as [string, string]
  const result = await getDocumentationV1ExtensionsNamespaceNameReleasesVersionDocumentationGet({
    client: createClient({ baseUrl: registryOrigin(origin).origin }),
    path: { namespace, name: localName, version },
    credentials: 'omit',
    headers: { Accept: 'application/json' },
  })
  if (result.response?.status === 404) return null
  if (!result.response?.ok) {
    throw new RegistryDocumentationError(
      result.response
        ? `Extension documentation request failed with HTTP ${result.response.status}.`
        : 'Extension documentation request could not reach the Registry.',
    )
  }
  const parsed = zReleaseDocumentation.safeParse(result.data)
  if (
    !parsed.success ||
    parsed.data.name !== name ||
    parsed.data.version !== version ||
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
