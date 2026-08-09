import { describe, expect, it } from 'vitest'

import { ExtensionLifecycleController, ExtensionState } from '../src'

describe('ExtensionLifecycleController', () => {
  it('runs the complete enable/disable sequence and never reports a failed activation as active', async () => {
    const calls: string[] = []
    const controller = new ExtensionLifecycleController(async () => {
      calls.push('load')
      return {
        async initialize() {
          calls.push('initialize')
        },
        async activate() {
          calls.push('activate')
        },
        async deactivate() {
          calls.push('deactivate')
        },
        async dispose() {
          calls.push('dispose')
        },
      }
    })

    await controller.enable()
    expect(controller.state).toEqual({ status: ExtensionState.ACTIVE, error: null })
    await controller.disable()
    expect(controller.state).toEqual({ status: ExtensionState.DISPOSED, error: null })
    expect(calls).toEqual(['load', 'initialize', 'activate', 'deactivate', 'dispose'])

    const failedCalls: string[] = []
    const failedController = new ExtensionLifecycleController(async () => {
      failedCalls.push('load')
      return {
        async initialize() {
          failedCalls.push('initialize')
        },
        async activate() {
          failedCalls.push('activate')
          throw new Error('activation exploded')
        },
        async deactivate() {
          failedCalls.push('deactivate')
        },
        async dispose() {
          failedCalls.push('dispose')
        },
      }
    })

    await expect(failedController.enable()).rejects.toThrow('activation exploded')
    expect(failedController.state.status).toBe(ExtensionState.ERROR)
    expect(failedController.state.error?.message).toContain('activation exploded')
    expect(failedCalls).toEqual(['load', 'initialize', 'activate', 'deactivate', 'dispose'])
  })
})
