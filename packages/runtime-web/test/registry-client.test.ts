import { afterEach, describe, expect, it, vi } from 'vitest'

import { RegistryClient } from '../src'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('RegistryClient', () => {
  it('preserves the browser receiver required by the default fetch implementation', async () => {
    const browserFetch = vi.fn(function (this: unknown) {
      if (this !== globalThis) throw new TypeError('Illegal invocation')
      return Promise.resolve(
        new Response(
          JSON.stringify({
            namespace: 'inkcre',
            name: 'twitter',
            version: '0.1.0',
            state: 'published',
            targets: [],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    }) as unknown as typeof globalThis.fetch
    vi.stubGlobal('fetch', browserFetch)

    const release = await new RegistryClient('https://registry.example').getPublishedRelease(
      'inkcre',
      'twitter',
      '0.1.0',
    )

    expect(release).toMatchObject({ namespace: 'inkcre', name: 'twitter', version: '0.1.0' })
    expect(browserFetch).toHaveBeenCalledOnce()
  })
})
