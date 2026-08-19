import type { ModuleFederation } from '@module-federation/runtime'
import { asError, combinedError } from './errors'

export interface WebExtensionModule {
  initialize?(): void | Promise<void>
  activate?(): void | Promise<void>
  deactivate?(): void | Promise<void>
  dispose?(): void | Promise<void>
}

export class WebExtensionModuleHandle<T extends WebExtensionModule = WebExtensionModule> {
  #active = false
  #disposed = false

  constructor(
    readonly name: string,
    readonly version: string,
    readonly module: T,
  ) {}

  async activate(): Promise<void> {
    if (this.#active) return
    try {
      await this.module.initialize?.()
      await this.module.activate?.()
      this.#active = true
    } catch (startError) {
      try {
        await this.dispose()
      } catch (cleanupError) {
        throw combinedError('Extension activation and compensation failed.', [
          asError(startError),
          asError(cleanupError),
        ])
      }
      throw startError
    }
  }

  async deactivate(): Promise<void> {
    if (this.#active) {
      await this.module.deactivate?.()
      this.#active = false
    }
  }

  async dispose(): Promise<void> {
    if (this.#disposed) return
    await this.deactivate()
    await this.module.dispose?.()
    this.#disposed = true
  }
}

export async function loadExtensionModule<T extends WebExtensionModule>(
  moduleFederation: ModuleFederation,
  name: string,
  version: string,
  manifestUrl: string,
): Promise<WebExtensionModuleHandle<T>> {
  const remoteName = webExtensionRemoteName(name)
  moduleFederation.registerRemotes([{ name: remoteName, entry: manifestUrl }], { force: true })
  const loaded = await moduleFederation.loadRemote<T | { default: T }>(remoteName)
  if (!loaded) throw new Error(`${name}@${version} returned no Module Federation module.`)
  const extensionModule = 'default' in loaded ? loaded.default : loaded
  return new WebExtensionModuleHandle(name, version, extensionModule)
}

export function webExtensionRemoteName(name: string): string {
  return `extension.${name.replace('/', '.')}`
}
