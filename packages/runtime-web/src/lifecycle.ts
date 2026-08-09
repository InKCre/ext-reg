export type Awaitable<T> = T | PromiseLike<T>

/** The four host-controlled hooks exported by an Extension remote. */
export interface ExtensionModule {
  initialize?(): Awaitable<void>
  activate?(): Awaitable<void>
  deactivate?(): Awaitable<void>
  dispose?(): Awaitable<void>
}

export type LoadedExtensionModule = ExtensionModule | { readonly default: ExtensionModule }
export type ExtensionLoader = () => Awaitable<LoadedExtensionModule>

export const ExtensionState = {
  IDLE: 'IDLE',
  LOADING: 'LOADING',
  LOADED: 'LOADED',
  INITIALIZING: 'INITIALIZING',
  READY: 'READY',
  ACTIVATING: 'ACTIVATING',
  ACTIVE: 'ACTIVE',
  DEACTIVATING: 'DEACTIVATING',
  DISPOSING: 'DISPOSING',
  DISPOSED: 'DISPOSED',
  ERROR: 'ERROR',
} as const

export type ExtensionState = (typeof ExtensionState)[keyof typeof ExtensionState]

export interface ExtensionRuntimeState {
  readonly status: ExtensionState
  readonly error: Error | null
}

export class LifecycleTransitionError extends Error {
  constructor(operation: 'enable' | 'disable', state: ExtensionState) {
    super(`Cannot ${operation} an Extension from lifecycle state ${state}`)
    this.name = 'LifecycleTransitionError'
  }
}

/**
 * Owns only volatile runtime state. Persisting an enabled peer binding remains
 * the host adapter's responsibility after enable() resolves successfully.
 */
export class ExtensionLifecycleController {
  readonly #loader: ExtensionLoader
  #runtimeState: ExtensionRuntimeState = Object.freeze({
    status: ExtensionState.IDLE,
    error: null,
  })
  #module: ExtensionModule | null = null

  constructor(loader: ExtensionLoader) {
    this.#loader = loader
  }

  get state(): ExtensionRuntimeState {
    return this.#runtimeState
  }

  get module(): ExtensionModule | null {
    return this.#module
  }

  async enable(): Promise<void> {
    if (
      this.state.status !== ExtensionState.IDLE &&
      this.state.status !== ExtensionState.DISPOSED
    ) {
      throw new LifecycleTransitionError('enable', this.state.status)
    }

    let initializationStarted = false
    let activationStarted = false

    try {
      this.#transition(ExtensionState.LOADING)
      this.#module = unwrapExtensionModule(await this.#loader())
      this.#transition(ExtensionState.LOADED)

      initializationStarted = true
      this.#transition(ExtensionState.INITIALIZING)
      await this.#module.initialize?.()
      this.#transition(ExtensionState.READY)

      activationStarted = true
      this.#transition(ExtensionState.ACTIVATING)
      await this.#module.activate?.()
      this.#transition(ExtensionState.ACTIVE)
    } catch (cause) {
      const primaryError = asError(cause)
      const cleanupErrors = await this.#compensateFailedEnable(
        initializationStarted,
        activationStarted,
      )
      const failure = combineErrors('Extension enable failed', primaryError, cleanupErrors)
      this.#module = null
      this.#transition(ExtensionState.ERROR, failure)
      throw failure
    }
  }

  async disable(): Promise<void> {
    if (this.state.status !== ExtensionState.ACTIVE || this.#module === null) {
      throw new LifecycleTransitionError('disable', this.state.status)
    }

    const failures: Error[] = []

    this.#transition(ExtensionState.DEACTIVATING)
    try {
      await this.#module.deactivate?.()
    } catch (cause) {
      failures.push(asError(cause))
    }

    this.#transition(ExtensionState.DISPOSING)
    try {
      await this.#module.dispose?.()
    } catch (cause) {
      failures.push(asError(cause))
    }

    if (failures.length > 0) {
      const [primaryError, ...cleanupErrors] = failures
      const failure = combineErrors('Extension disable failed', primaryError, cleanupErrors)
      this.#transition(ExtensionState.ERROR, failure)
      throw failure
    }

    this.#module = null
    this.#transition(ExtensionState.DISPOSED)
  }

  async #compensateFailedEnable(
    initializationStarted: boolean,
    activationStarted: boolean,
  ): Promise<Error[]> {
    if (this.#module === null) {
      return []
    }

    const failures: Error[] = []

    if (activationStarted) {
      try {
        await this.#module.deactivate?.()
      } catch (cause) {
        failures.push(asError(cause))
      }
    }

    if (initializationStarted) {
      try {
        await this.#module.dispose?.()
      } catch (cause) {
        failures.push(asError(cause))
      }
    }

    return failures
  }

  #transition(status: ExtensionState, error: Error | null = null): void {
    this.#runtimeState = Object.freeze({ status, error })
  }
}

function unwrapExtensionModule(loaded: LoadedExtensionModule): ExtensionModule {
  if (typeof loaded !== 'object' || loaded === null) {
    throw new TypeError('Extension loader returned no module')
  }

  const module = 'default' in loaded ? loaded.default : loaded
  if (typeof module !== 'object' || module === null) {
    throw new TypeError('Extension loader returned an invalid module')
  }

  for (const hook of ['initialize', 'activate', 'deactivate', 'dispose'] as const) {
    if (module[hook] !== undefined && typeof module[hook] !== 'function') {
      throw new TypeError(`Extension hook ${hook} must be a function`)
    }
  }

  return module
}

function asError(cause: unknown): Error {
  return cause instanceof Error ? cause : new Error(String(cause))
}

function combineErrors(
  message: string,
  primaryError: Error,
  cleanupErrors: readonly Error[],
): Error {
  if (cleanupErrors.length === 0) {
    return primaryError
  }

  return new AggregateError([primaryError, ...cleanupErrors], `${message}: ${primaryError.message}`)
}
