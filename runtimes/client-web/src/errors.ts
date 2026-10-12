export class WebExtensionRuntimeError extends Error {
  override name = 'WebExtensionRuntimeError'
}

export class RegistryReleaseError extends WebExtensionRuntimeError {
  override name = 'RegistryReleaseError'
}

export class RegistryReleaseUnavailableError extends RegistryReleaseError {
  override name = 'RegistryReleaseUnavailableError'

  constructor(readonly status: 404 | 451) {
    super(`Extension Release is unavailable (HTTP ${status}).`)
  }
}

export type NativeDistributionFormat = 'python' | 'module_federation'

export class NativeDistributionSupportChangeError extends WebExtensionRuntimeError {
  override name = 'NativeDistributionSupportChangeError'

  constructor(
    readonly extensionName: string,
    readonly installedVersion: string,
    readonly targetVersion: string,
    readonly removedFormats: readonly NativeDistributionFormat[],
    readonly reason: 'reduced' | 'unavailable',
  ) {
    super(
      reason === 'reduced'
        ? `${extensionName}@${targetVersion} removes native support: ${removedFormats.join(', ')}.`
        : `Cannot verify native support of installed ${extensionName}@${installedVersion}.`,
    )
  }
}

export class RegistryDocumentationError extends WebExtensionRuntimeError {
  override name = 'RegistryDocumentationError'
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
