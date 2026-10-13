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
  readonly #intents = new Map<string, Promise<unknown>>()
  readonly #operations = new Map<string, Promise<unknown>>()
  readonly #startups = new Set<Promise<void>>()
  #closing = false

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
    this.#assertOpen()
    return this.#ordered(this.#operations, input.name, async () => {
      const current = await ExtensionParticipationModel.get(peerId, input.name)
      if (current) {
        if (current.distribution === 'module_federation' && current.version === input.version)
          return current
        return this.#changeVersion(input.name, input.version, peerId)
      }
      const release = await this.#releases.get(input.name, input.version, true)
      await ExtensionModel.install({ name: release.name, nickname: release.nickname })
      return ExtensionParticipationModel.select({
        peerId,
        name: release.name,
        distribution: 'module_federation',
        version: release.version,
      })
    })
  }

  async changeVersion(
    name: string,
    version: string,
    peerId: string,
  ): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    this.#assertOpen()
    return this.#ordered(this.#operations, name, () => this.#changeVersion(name, version, peerId))
  }

  async #changeVersion(
    name: string,
    version: string,
    peerId: string,
  ): Promise<ExtensionParticipationModel> {
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
    this.#assertOpen()
    await this.#ordered(this.#operations, name, async () => {
      if (this.#running.has(name)) throw new ExtensionEnabledError(name)
      await (await this.#requireParticipation(name, peerId)).remove()
      this.#errors.delete(name)
    })
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
    this.#assertOpen()
    await this.#ordered(this.#intents, name, async () => {
      const participation = await this.#resolveLegacy(
        await this.#requireParticipation(name, peerId),
      )
      await participation.setEnabled(true)
    })
    return this.#ordered(this.#operations, name, async () => {
      try {
        const current = await this.#restore(name, peerId)
        if (!current) throw new WebExtensionRuntimeError('The Peer selection was removed.')
        return current
      } catch (error) {
        this.#errors.set(name, asError(error))
        throw error
      }
    })
  }

  async disable(name: string, peerId: string): Promise<ExtensionParticipationModel> {
    this.#assertPeer(peerId)
    this.#assertOpen()
    // Commit the command before waiting for an in-flight restore to finish.
    await this.#ordered(this.#intents, name, async () => {
      await (await this.#requireParticipation(name, peerId)).setEnabled(false)
    })
    return this.#ordered(this.#operations, name, async () => {
      try {
        await this.#stop(name)
        this.#errors.delete(name)
        return await this.#requireParticipation(name, peerId)
      } catch (error) {
        this.#errors.set(name, asError(error))
        throw error
      }
    })
  }

  async startup(peerId: string): Promise<void> {
    this.#assertPeer(peerId)
    this.#assertOpen()
    const task = this.#restoreAll(peerId)
    this.#startups.add(task)
    void task.finally(() => this.#startups.delete(task)).catch(() => {})
    return task
  }

  async #restoreAll(peerId: string): Promise<void> {
    const failures: Error[] = []
    const rows = await ExtensionParticipationModel.list(peerId)
    const names = new Set([...rows.map((row) => row.name), ...this.#running.keys()])
    for (const name of names) {
      try {
        await this.#ordered(this.#operations, name, () => this.#restore(name, peerId))
      } catch (error) {
        const failure = asError(error)
        this.#errors.set(name, failure)
        failures.push(failure)
      }
    }
    if (failures.length) throw combinedError('Web Extension startup failed.', failures)
  }

  async shutdown(): Promise<void> {
    this.#closing = true
    try {
      // Pending list/intent work must not activate after shutdown has returned.
      while (this.#startups.size || this.#intents.size || this.#operations.size) {
        await Promise.allSettled([
          ...this.#startups,
          ...this.#intents.values(),
          ...this.#operations.values(),
        ])
      }
      const failures: Error[] = []
      for (const name of this.#running.keys()) {
        try {
          await this.#stop(name)
        } catch (error) {
          failures.push(asError(error))
        }
      }
      if (failures.length) throw combinedError('Web Extension shutdown failed.', failures)
    } finally {
      this.#closing = false
    }
  }

  async #stop(name: string): Promise<void> {
    const handle = this.#running.get(name)
    if (!handle) return
    await handle.dispose()
    this.#running.delete(name)
  }

  async #resolveLegacy(row: ExtensionParticipationModel): Promise<ExtensionParticipationModel> {
    if (row.distribution === 'module_federation') return row
    if (row.distribution !== null)
      throw new WebExtensionRuntimeError('The selected distribution cannot run in this Peer.')
    await this.#releases.get(row.name, row.version, false)
    return ExtensionParticipationModel.select({
      peerId: row.peer_id,
      name: row.name,
      distribution: 'module_federation',
      version: row.version,
      expectedVersion: row.version,
    })
  }

  #matches(
    current: ExtensionParticipationModel | null,
    selected: ExtensionParticipationModel,
  ): boolean {
    return (
      !this.#closing &&
      current !== null &&
      current.enabled &&
      current.distribution === 'module_federation' &&
      current.version === selected.version &&
      current.distribution === selected.distribution
    )
  }

  async #restore(name: string, peerId: string): Promise<ExtensionParticipationModel | null> {
    let selected = await ExtensionParticipationModel.get(peerId, name)
    const running = this.#running.get(name)
    if (running) {
      if (
        !this.#closing &&
        selected?.enabled &&
        selected.distribution === 'module_federation' &&
        selected.version === running.version
      )
        return selected
      await this.#stop(name)
    }
    if (this.#closing || !selected?.enabled) return selected
    selected = await this.#resolveLegacy(selected)
    let current = await ExtensionParticipationModel.get(peerId, name)
    if (!this.#matches(current, selected)) return current
    const release = await this.#releases.get(name, selected.version, false)
    this.#warnIfYanked(release)
    const handle = await loadExtensionModule<T>(
      this.#moduleFederation,
      name,
      selected.version,
      release.module_federation!.manifest_url,
    )
    try {
      current = await ExtensionParticipationModel.get(peerId, name)
      if (!this.#matches(current, selected)) {
        await handle.dispose()
        return current
      }
      await handle.activate()
      // Other admitted clients may change a sleeping Peer directly in the shared store.
      // A local queue does not claim ownership of their durable intent.
      current = await ExtensionParticipationModel.get(peerId, name)
      if (!this.#matches(current, selected)) {
        await handle.dispose()
        return current
      }
    } catch (startError) {
      try {
        await handle.dispose()
      } catch (cleanupError) {
        throw combinedError('Extension restore and compensation failed.', [
          asError(startError),
          asError(cleanupError),
        ])
      }
      throw startError
    }
    this.#running.set(name, handle)
    this.#errors.delete(name)
    return current
  }

  #ordered<R>(
    queue: Map<string, Promise<unknown>>,
    name: string,
    work: () => Promise<R>,
  ): Promise<R> {
    const previous = queue.get(name) ?? Promise.resolve()
    const task = previous.catch(() => {}).then(work)
    queue.set(name, task)
    void task
      .finally(() => {
        if (queue.get(name) === task) queue.delete(name)
      })
      .catch(() => {})
    return task
  }

  #assertOpen(): void {
    if (this.#closing) throw new WebExtensionRuntimeError('The runtime is shutting down.')
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
