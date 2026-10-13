import {
  InstalledExtensionSchema,
  PeerManager,
  PeerProtocolResponseSchema,
  type InstalledExtension,
  type JsonValue,
  type Peer,
} from '@inkcre/core'
import { WebExtensionRuntimeError } from './errors'

export const EXTENSION_MANAGEMENT_CAPABILITY = 'core.extension.management.v1'

export type ExtensionManagementCommand =
  | { action: 'install'; extension: string; version: string }
  | { action: 'enable' | 'disable'; extension: string }
  | { action: 'patch_config'; extension: string; patch: Record<string, JsonValue> }

/** Live advertisements are discovery candidates, not proof of a usable outbound route. */
export async function listAdvertisedExtensionManagementPeers(): Promise<Peer[]> {
  return (await PeerManager.listLive()).filter((peer) => {
    try {
      return peer.capabilitySnapshot().some(({ id }) => id === EXTENSION_MANAGEMENT_CAPABILITY)
    } catch {
      return false
    }
  })
}

/** Send once to the selected Peer. PeerManager retains transport failure classification. */
export async function manageExtensionOnPeer(
  peerId: string,
  command: ExtensionManagementCommand,
): Promise<InstalledExtension> {
  if (!peerId) throw new TypeError('Extension management requires an exact Peer ID.')
  const result = await PeerManager.delegate(
    EXTENSION_MANAGEMENT_CAPABILITY,
    { body: command },
    peerId,
  )
  const response = PeerProtocolResponseSchema.safeParse(result)
  if (!response.success) {
    throw new WebExtensionRuntimeError('Extension management Peer returned an invalid response.')
  }
  if (response.data.status !== 200) {
    throw new WebExtensionRuntimeError(
      `Extension management Peer returned HTTP ${response.data.status}.`,
    )
  }
  const extension = InstalledExtensionSchema.safeParse(response.data.body)
  // Validation issues and remote error bodies can contain configuration credentials.
  if (!extension.success || extension.data.name !== command.extension) {
    throw new WebExtensionRuntimeError('Extension management Peer returned an invalid Extension.')
  }
  return extension.data
}
