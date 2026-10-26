import { z } from 'zod'
import {
  ExtensionRuntimeStatusSchema,
  PeerManager,
  PeerProtocolResponseSchema,
  type ExtensionRuntimeStatus,
  type JsonValue,
  type Peer,
} from '@inkcre/core'
import { WebExtensionRuntimeError } from './errors'

export const EXTENSION_MANAGEMENT_CAPABILITY = 'core.extension.management.v2'

export type ExtensionManagementCommand =
  | {
      action: 'select'
      extension: string
      distribution: string
      version: string
    }
  | { action: 'enable' | 'disable' | 'unselect'; extension: string }
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

const ExtensionPeerStatusSchema = z.object({
  peer_id: z.uuid(),
  supported_distributions: z.array(z.string().min(1)),
  extensions: z.array(z.unknown()),
})
export interface ExtensionPeerStatus {
  peer_id: string
  supported_distributions: string[]
  extensions: ExtensionRuntimeStatus[]
}

async function sendCommand(
  peerId: string,
  command: ExtensionManagementCommand | { action: 'status'; extension?: string },
): Promise<ExtensionPeerStatus> {
  if (!peerId) throw new TypeError('Extension management requires an exact Peer ID.')
  const result = await PeerManager.delegate(
    EXTENSION_MANAGEMENT_CAPABILITY,
    { body: command },
    peerId,
  )
  const response = PeerProtocolResponseSchema.safeParse(result)
  if (!response.success)
    throw new WebExtensionRuntimeError('Extension management Peer returned an invalid response.')
  if (response.data.status !== 200)
    throw new WebExtensionRuntimeError(
      `Extension management Peer returned HTTP ${response.data.status}.`,
    )
  const status = ExtensionPeerStatusSchema.safeParse(response.data.body)
  // Remote bodies and validation issues may contain configuration credentials.
  if (!status.success || status.data.peer_id !== peerId) {
    throw new WebExtensionRuntimeError('Extension management Peer returned an invalid status.')
  }
  const extensions = status.data.extensions.map((row) => {
    const parsed = ExtensionRuntimeStatusSchema.safeParse(row)
    if (!parsed.success || parsed.data.peer_id !== peerId) {
      throw new WebExtensionRuntimeError('Extension management Peer returned an invalid status.')
    }
    return parsed.data
  })
  return { ...status.data, extensions }
}

/** Read capability support and actual runtime facts from the exact target once. */
export function readExtensionPeerStatus(
  peerId: string,
  extension?: string,
): Promise<ExtensionPeerStatus> {
  return sendCommand(peerId, { action: 'status', ...(extension ? { extension } : {}) })
}

/** PeerManager retains transport failure classification; no target substitution or retry. */
export async function manageExtensionOnPeer(
  peerId: string,
  command: ExtensionManagementCommand,
): Promise<ExtensionRuntimeStatus> {
  const status = await sendCommand(peerId, command)
  const extension = status.extensions.find((row) => row.name === command.extension)
  if (!extension)
    throw new WebExtensionRuntimeError(
      'Extension management Peer returned no exact Extension status.',
    )
  return extension
}
