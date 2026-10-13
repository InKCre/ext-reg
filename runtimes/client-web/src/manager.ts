import type { ModuleFederation } from '@module-federation/runtime'
import {
  ExtensionModel,
  ExtensionParticipationModel,
  type ExtensionRuntimeStatus,
} from '@inkcre/core'
import type { NativeReleaseRecord as ReleaseRecord } from './generated/types.gen'
import { asError, combinedError, ExtensionEnabledError, WebExtensionRuntimeError } from './errors'
import { loadExtensionModule, type WebExtensionModule, WebExtensionModuleHandle } from './module'
import { RegistryReleaseReader } from './registry'

export interface ExtensionManagerOptions {
  readonly peerId: string
  readonly releases: RegistryReleaseReader
  readonly moduleFederation: ModuleFederation
  readonly warn?: (message: string) => void
}

export interface InstallExtensionInput {
  readonly name: string
  readonly version: string
}

export class ExtensionManager<T extends WebExtensionModule = WebExtensionModule> {
  readonly #peerId: string
  readonly #releases: RegistryReleaseReader
  readonly #moduleFederation: ModuleFederation
  readonly #warn: (message: string) => void
  readonly #running = new Map<string, WebExtensionModuleHandle<T>>()
  readonly #errors = new Map<string, Error>()

  constructor(options: ExtensionManagerOptions) {
    if (!options.peerId) throw new TypeError('An exact runtime Peer ID is required.')
    this.#peerId = options.peerId
    this.#releases = options.releases
    this.#moduleFederation = options.moduleFederation
    this.#warn = options.warn ?? console.warn
  }

  list(): Promise<ExtensionModel[]> {
    return ExtensionModel.list()
  }

  get(name: string): Promise<ExtensionModel | null> {
    return ExtensionModel.get(name)
  }

  async install(
    input: InstallExtensionInput,
    peerId: string,
  ): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    const current = await ExtensionParticipationModel.get(peerId, input.name)
    if (current) {
      if (current.distribution === 'module_federation' && current.version === input.version)
        return current
      return this.changeVersion(input.name, input.version, peerId)
    }
    const release = await this.#releases.get(input.name, input.version, true)
    await ExtensionModel.install({ name: release.name, nickname: release.nickname })
    return ExtensionParticipationModel.select({
      peerId,
      name: release.name,
      distribution: 'module_federation',
      version: release.version,
    })
  }

  async changeVersion(
    name: string,
    version: string,
    peerId: string,
  ): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    const current = await this.#requireParticipation(name, peerId)
    if (this.#running.has(name)) throw new ExtensionEnabledError(name)
    const release = await this.#releases.get(name, version, true)
    return ExtensionParticipationModel.select({
      peerId,
      name,
      distribution: 'module_federation',
      version: release.version,
      expectedVersion: current.version,
    })
  }

  async updateConfig(name: string, config: Record<string, unknown>): Promise<ExtensionModel> {
    return (await this.#requireInstalled(name)).updateConfig(config)
  }

  async uninstall(name: string, peerId: string): Promise<void> {
    this.#assertPeer(peerId)
    if (this.#running.has(name)) throw new ExtensionEnabledError(name)
    await (await this.#requireParticipation(name, peerId)).remove()
    this.#errors.delete(name)
  }

  async getStatus(name: string, peerId: string = this.#peerId): Promise<ExtensionRuntimeStatus> {
    this.#assertPeer(peerId)
    const participation = await ExtensionParticipationModel.get(peerId, name)
    const handle = this.#running.get(name)
    return {
      name,
      peer_id: peerId,
      supported_distributions: ['module_federation'],
      distribution: participation?.distribution ?? null,
      version: participation?.version ?? null,
      enabled: participation?.enabled ?? false,
      config_schema: participation?.config_schema ?? null,
      loaded_version: handle?.version ?? null,
      running: !!handle,
      restart_required: false,
      operation: null,
      error: this.#errors.get(name)?.message ?? null,
    }
  }

  async listStatus(peerId: string = this.#peerId): Promise<ExtensionRuntimeStatus[]> {
    this.#assertPeer(peerId)
    return Promise.all(
      (await ExtensionParticipationModel.list(peerId)).map((row) =>
        this.getStatus(row.name, peerId),
      ),
    )
  }

  isRunning(name: string): boolean {
    return this.#running.has(name)
  }

  getModule(name: string): T | null {
    return this.#running.get(name)?.module ?? null
  }

  getRuntimeError(name: string): Error | null {
    return this.#errors.get(name) ?? null
  }

  async enable(name: string, peerId: string): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    let participation = await this.#requireParticipation(name, peerId)
    if (participation.distribution === null) {
      await this.#releases.get(name, participation.version, false)
      participation = await ExtensionParticipationModel.select({
        peerId,
        name,
        distribution: 'module_federation',
        version: participation.version,
        expectedVersion: participation.version,
      })
    }
    const handle = await this.#start(participation)
    try {
      return await participation.setEnabled(true)
    } catch (error) {
      try {
        await handle.dispose()
        this.#running.delete(name)
      } catch (cleanupError) {
        throw combinedError('Enable persistence and runtime compensation failed.', [
          asError(error),
          asError(cleanupError),
        ])
      }
      throw error
    }
  }

  async disable(name: string, peerId: string): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    const participation = await this.#requireParticipation(name, peerId)
    const handle = this.#running.get(name)
    if (handle) {
      await handle.dispose()
      this.#running.delete(name)
    }
    try {
      return await participation.setEnabled(false)
    } catch (error) {
      if (handle) {
        try {
          await this.#start(participation)
        } catch (restartError) {
          throw combinedError('Disable persistence and runtime restoration failed.', [
            asError(error),
            asError(restartError),
          ])
        }
      }
      throw error
    }
  }

  async startup(peerId: string): Promise<void> {
    this.#assertPeer(peerId)
    const failures: Error[] = []
    for (const participation of await ExtensionParticipationModel.list(peerId)) {
      if (!participation.enabled) continue
      try {
        await this.enable(participation.name, peerId)
      } catch (error) {
        const failure = asError(error)
        this.#errors.set(participation.name, failure)
        failures.push(failure)
      }
    }
    if (failures.length) throw combinedError('Web Extension startup failed.', failures)
  }

  async shutdown(): Promise<void> {
    const failures: Error[] = []
    for (const [name, handle] of this.#running) {
      try {
        await handle.dispose()
        this.#running.delete(name)
      } catch (error) {
        failures.push(asError(error))
      }
    }
    if (failures.length) throw combinedError('Web Extension shutdown failed.', failures)
  }

  async #start(extension: ExtensionParticipationModel): Promise<WebExtensionModuleHandle<T>> {
    const running = this.#running.get(extension.name)
    if (running) {
      if (running.version !== extension.version)
        throw new WebExtensionRuntimeError('A different exact version is running.')
      return running
    }
    if (extension.distribution !== 'module_federation')
      throw new WebExtensionRuntimeError('The selected distribution cannot run in this Peer.')
    const release = await this.#releases.get(extension.name, extension.version, false)
    this.#warnIfYanked(release)
    const distribution = release.module_federation!
    const handle = await loadExtensionModule<T>(
      this.#moduleFederation,
      extension.name,
      extension.version,
      distribution.manifest_url,
    )
    await handle.activate()
    this.#running.set(extension.name, handle)
    this.#errors.delete(extension.name)
    return handle
  }

  async #requireInstalled(name: string): Promise<ExtensionModel> {
    const extension = await ExtensionModel.get(name)
    if (!extension) throw new WebExtensionRuntimeError(`Extension ${name} is not installed.`)
    return extension
  }

  #assertPeer(peerId: string): void {
    if (peerId !== this.#peerId)
      throw new WebExtensionRuntimeError('The runtime belongs to a different Peer.')
  }

  async #requireParticipation(name: string, peerId: string): Promise<ExtensionParticipationModel> {
    if (!peerId) throw new TypeError('An exact Peer ID is required.')
    const participation = await ExtensionParticipationModel.get(peerId, name)
    if (!participation)
      throw new WebExtensionRuntimeError(`Extension ${name} is not selected for ${peerId}.`)
    return participation
  }

  #warnIfYanked(release: ReleaseRecord): void {
    if (release.state === 'yanked')
      this.#warn(`Starting exact installed yanked Release ${release.name}@${release.version}.`)
  }
}
