export class WebExtensionRuntimeError extends Error {
  override name = 'WebExtensionRuntimeError'
}

export class RegistryReleaseError extends WebExtensionRuntimeError {
  override name = 'RegistryReleaseError'
}

export class HostSdkCompatibilityError extends WebExtensionRuntimeError {
  override name = 'HostSdkCompatibilityError'
}

export class ModuleLifecycleError extends WebExtensionRuntimeError {
  override name = 'ModuleLifecycleError'
}

export class ExtensionEnabledError extends WebExtensionRuntimeError {
  override name = 'ExtensionEnabledError'

  constructor(name: string) {
    super(`Cannot change or uninstall ${name} while one or more Peers remain enabled.`)
  }
}

export function asError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error))
}

export function combinedError(message: string, errors: readonly Error[]): Error {
  if (errors.length === 1) return errors[0]
  return new ModuleLifecycleError(`${message} ${errors.map((error) => error.message).join(' | ')}`)
}
