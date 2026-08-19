import type { ModuleFederation } from '@module-federation/runtime'
import { ExtensionModel } from '@inkcre/core'
import type { ReleaseRecord } from './generated/types.gen'
import { asError, combinedError, ExtensionEnabledError, WebExtensionRuntimeError } from './errors'
import { loadExtensionModule, type WebExtensionModule, WebExtensionModuleHandle } from './module'
import { RegistryReleaseReader } from './registry'

export interface ExtensionManagerOptions {
  readonly releases: RegistryReleaseReader
  readonly moduleFederation: ModuleFederation
  readonly warn?: (message: string) => void
}

export interface InstallExtensionInput {
  readonly name: string
  readonly version: string
}

export class ExtensionManager<T extends WebExtensionModule = WebExtensionModule> {
  readonly #releases: RegistryReleaseReader
  readonly #moduleFederation: ModuleFederation
  readonly #warn: (message: string) => void
  readonly #running = new Map<string, WebExtensionModuleHandle<T>>()
  readonly #errors = new Map<string, Error>()

  constructor(options: ExtensionManagerOptions) {
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

  async install(input: InstallExtensionInput): Promise<ExtensionModel> {
    const release = await this.#releases.get(input.name, input.version, true)
    return ExtensionModel.install({
      name: release.name,
      version: release.version,
      nickname: release.nickname,
    })
  }

  async changeVersion(name: string, version: string): Promise<ExtensionModel> {
    const extension = await this.#requireInstalled(name)
    this.#assertStoppedAndDisabled(extension)
    if (extension.version === version) return extension
    const release = await this.#releases.get(name, version, true)
    return extension.changeVersion(release.version, release.nickname)
  }

  async updateConfig(name: string, config: Record<string, unknown>): Promise<ExtensionModel> {
    return (await this.#requireInstalled(name)).updateConfig(config)
  }

  async uninstall(name: string): Promise<void> {
    const extension = await this.#requireInstalled(name)
    this.#assertStoppedAndDisabled(extension)
    await extension.uninstall()
    this.#errors.delete(name)
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

  async enable(name: string, peerId: string): Promise<ExtensionModel> {
    const extension = await this.#requireInstalled(name)
    const handle = await this.#start(extension)
    if (extension.enabled.includes(peerId)) return extension
    try {
      const enabled = await extension.enablePeer(peerId)
      if (!enabled.enabled.includes(peerId))
        throw new Error(`${extension.name} was not enabled for ${peerId}.`)
      if (enabled.version !== extension.version)
        throw new Error(`${extension.name} changed version during enable.`)
      return enabled
    } catch (persistenceError) {
      try {
        await handle.dispose()
        this.#running.delete(extension.name)
      } catch (cleanupError) {
        throw combinedError('Enable persistence and runtime compensation failed.', [
          asError(persistenceError),
          asError(cleanupError),
        ])
      }
      throw persistenceError
    }
  }

  async disable(name: string, peerId: string): Promise<ExtensionModel> {
    const extension = await this.#requireInstalled(name)
    if (!extension.enabled.includes(peerId)) return extension
    const handle = this.#running.get(extension.name)
    if (handle) {
      await handle.dispose()
      this.#running.delete(extension.name)
    }
    try {
      return await extension.disablePeer(peerId)
    } catch (persistenceError) {
      if (handle) {
        try {
          await this.#start(extension)
        } catch (restartError) {
          throw combinedError('Disable persistence and runtime restoration failed.', [
            asError(persistenceError),
            asError(restartError),
          ])
        }
      }
      throw persistenceError
    }
  }

  async startup(peerId: string): Promise<void> {
    const extensions = await ExtensionModel.list()
    const failures: Error[] = []
    for (const extension of extensions.filter(({ enabled }) => enabled.includes(peerId))) {
      try {
        await this.#start(extension)
      } catch (error) {
        const failure = asError(error)
        this.#errors.set(extension.name, failure)
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

  async #start(extension: ExtensionModel): Promise<WebExtensionModuleHandle<T>> {
    const running = this.#running.get(extension.name)
    if (running) return running
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

  #assertStoppedAndDisabled(extension: ExtensionModel): void {
    if (extension.enabled.length > 0 || this.#running.has(extension.name)) {
      throw new ExtensionEnabledError(extension.name)
    }
  }

  #warnIfYanked(release: ReleaseRecord): void {
    if (release.state === 'yanked')
      this.#warn(`Starting exact installed yanked Release ${release.name}@${release.version}.`)
  }
}
