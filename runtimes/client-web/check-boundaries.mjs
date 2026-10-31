import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { once } from 'node:events'
import {
  configStore,
  PeerManager,
  PeerOutcomeUnknown,
  ExtensionParticipationModel,
} from '@inkcre/core'
import {
  EXTENSION_MANAGEMENT_CAPABILITY,
  ExtensionManager,
  ExtensionEnabledError,
  getExtensionDocumentation,
  listAdvertisedExtensionManagementPeers,
  manageExtensionOnPeer,
  preferredPublishedRelease,
  RegistryDocumentationError,
  RegistryReleaseReader,
  sortPublishedReleases,
  webExtensionRemoteName,
  WebExtensionModuleHandle,
} from './dist/index.js'

// An initialization failure can leave registrations that the module owns.
// The Host must call its existing dispose hook before returning that failure.
const initialized = []
const partialFailure = new Error('Partial initialization failed')
const partialModule = new WebExtensionModuleHandle('inkcre/partial', '1.0.0', {
  initialize() {
    initialized.push('initialize')
    throw partialFailure
  },
  activate() {
    initialized.push('activate')
  },
  dispose() {
    initialized.push('dispose')
  },
})
await assert.rejects(partialModule.activate(), (error) => error === partialFailure)
await partialModule.dispose()
assert.deepEqual(initialized, ['initialize', 'dispose'])
// Disposal is terminal, including after partial startup. Reactivation would leave
// new resources behind because the next dispose call is already idempotent.
await assert.rejects(partialModule.activate(), /disposed Extension module/)
assert.deepEqual(initialized, ['initialize', 'dispose'])

// Exercise the built package and real SDK over HTTP, without a deployment or real credentials.
const target = '11111111-1111-4111-8111-111111111111'
const current = '22222222-2222-4222-8222-222222222222'
const secret = 'boundary-check-secret'
const installed = {
  name: 'inkcre/memos',
  peer_id: target,
  distribution: 'python',
  version: '0.2.0',
  enabled: true,
  config_schema: null,
  supported_distributions: ['python'],
  loaded_version: null,
  running: false,
  restart_required: true,
  operation: null,
  error: null,
}
const envelope = { peer_id: target, supported_distributions: ['python'], extensions: [installed] }
let origin
let managementStatus = 200
let managementBody = envelope
let dropManagement = false
let docStatus = 200
let docBody
let dropDocumentation = false
const catalogReleases = [
  {
    name: 'inkcre/catalog',
    nickname: 'Catalog check',
    version: '2.0.0-beta.1',
    state: 'published',
    distribution: 'module_federation',
    module_federation: {
      host_sdk: '@inkcre/core',
      host_sdk_version: '>=0.3.0 <0.4.0',
      manifest_url: '/mf-manifest.json',
    },
    python: null,
  },
  {
    name: 'inkcre/catalog',
    nickname: 'Catalog check',
    version: '1.10.0',
    state: 'published',
    distribution: 'module_federation',
    module_federation: {
      host_sdk: '@inkcre/core',
      host_sdk_version: '>=0.3.0 <0.4.0',
      manifest_url: '/mf-manifest.json',
    },
    python: null,
  },
  {
    name: 'inkcre/catalog',
    nickname: 'Catalog check',
    version: '1.2.0',
    state: 'published',
    distribution: 'module_federation',
    module_federation: {
      host_sdk: '@inkcre/core',
      host_sdk_version: '>=0.3.0 <0.4.0',
      manifest_url: '/mf-manifest.json',
    },
    python: null,
  },
]
const requests = []
const server = createServer(async (request, response) => {
  const url = new URL(request.url, origin)
  const chunks = []
  for await (const chunk of request) chunks.push(chunk)
  requests.push({ url, headers: request.headers, body: Buffer.concat(chunks).toString() })
  response.setHeader('Content-Type', 'application/json')
  if (url.pathname === '/peers') {
    const peer = (id, capabilities) => ({
      id,
      name: id,
      capabilities,
      lease_expires_at: '2099-01-01T00:00:00Z',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    })
    const advertisement = {
      id: EXTENSION_MANAGEMENT_CAPABILITY,
      inbound: {
        protocol: 'core.peer.protocol.http.v1',
        parameters: { method: 'POST', url: `${origin}/manage` },
      },
    }
    const peers = [
      peer(target, [advertisement]),
      peer(current, [{ ...advertisement, inbound: { protocol: 'unsupported', parameters: {} } }]),
      peer('33333333-3333-4333-8333-333333333333', [
        { ...advertisement, id: `${EXTENSION_MANAGEMENT_CAPABILITY}.other` },
      ]),
      peer('44444444-4444-4444-8444-444444444444', [{ id: EXTENSION_MANAGEMENT_CAPABILITY }]),
    ]
    response.end(
      JSON.stringify(url.searchParams.getAll('id').includes(`eq.${target}`) ? [peers[0]] : peers),
    )
  } else if (url.pathname === '/manage') {
    if (dropManagement) return request.socket.destroy()
    response.statusCode = managementStatus
    response.end(JSON.stringify(managementBody))
  } else if (url.pathname === '/v2/extensions') {
    response.end(JSON.stringify([{ name: 'inkcre/catalog', nickname: 'Catalog check' }]))
  } else if (url.pathname === '/v2/extensions/inkcre/catalog/distributions/module_federation') {
    response.end(
      JSON.stringify({
        name: 'inkcre/catalog',
        nickname: 'Catalog check',
        releases: catalogReleases,
      }),
    )
  } else if (
    url.pathname.startsWith(
      '/v2/extensions/inkcre/catalog/distributions/module_federation/releases/',
    )
  ) {
    const version = url.pathname.split('/').at(-1)
    response.end(JSON.stringify(catalogReleases.find((release) => release.version === version)))
  } else {
    if (dropDocumentation) return request.socket.destroy()
    response.statusCode = docStatus
    response.end(JSON.stringify(docBody))
  }
})
server.listen(0, '127.0.0.1')
await once(server, 'listening')
origin = `http://127.0.0.1:${server.address().port}`

try {
  assert.notEqual(
    webExtensionRemoteName('inkcre/memos', '0.2.0'),
    webExtensionRemoteName('inkcre/memos', '0.2.1'),
  )
  configStore.metaConfig = {
    INKCRE_PGREST_URL: origin,
    INKCRE_PEER_ID: current,
    INKCRE_JWT_SECRET: 'isolated-check-signing-secret-at-least-32-characters',
  }
  PeerManager.setupBuiltinOutbounds()
  const releases = new RegistryReleaseReader({
    registryOrigin: origin,
    hostSdk: { name: '@inkcre/core', version: '0.3.0' },
  })
  assert.deepEqual(await releases.list(), [{ name: 'inkcre/catalog', nickname: 'Catalog check' }])
  assert.equal((await releases.getExtension('inkcre/catalog')).releases.length, 3)
  assert.deepEqual(
    sortPublishedReleases(catalogReleases).map(({ version }) => version),
    ['2.0.0-beta.1', '1.10.0', '1.2.0'],
  )
  assert.equal(preferredPublishedRelease(catalogReleases).version, '1.10.0')
  assert.equal((await releases.getRelease('inkcre/catalog', '1.10.0', true)).version, '1.10.0')
  assert.equal(
    (await releases.get('inkcre/catalog', '1.10.0', true)).distribution,
    'module_federation',
  )
  const originalGet = ExtensionParticipationModel.get
  const selection = {
    name: 'inkcre/catalog',
    peer_id: current,
    distribution: 'module_federation',
    version: '1.10.0',
    enabled: true,
    config_schema: { type: 'object' },
    async setEnabled() {
      return this
    },
  }
  ExtensionParticipationModel.get = async () => selection
  const manager = new ExtensionManager({
    peerId: current,
    releases,
    moduleFederation: {
      registerRemotes() {},
      async loadRemote() {
        return {}
      },
    },
  })
  try {
    await assert.rejects(manager.getStatus(selection.name, target), /different Peer/)
    await manager.enable(selection.name, current)
    assert.equal(
      await manager.install({ name: selection.name, version: selection.version }, current),
      selection,
    )
    await assert.rejects(
      manager.install({ name: selection.name, version: '1.2.0' }, current),
      ExtensionEnabledError,
    )
    assert.equal(selection.version, '1.10.0')
    assert.deepEqual(selection.config_schema, { type: 'object' })
  } finally {
    await manager.shutdown()
    ExtensionParticipationModel.get = originalGet
  }
  // Restore consumes durable intent; delayed modules cannot resurrect revoked selections.
  const originalList = ExtensionParticipationModel.list
  const deferred = () => {
    let resolve
    const promise = new Promise((done) => {
      resolve = done
    })
    return { promise, resolve }
  }
  try {
    for (const scenario of [
      'pending-load-disable',
      'disable-command',
      'external-disable',
      'external-pin',
      'shutdown',
    ]) {
      const entered = deferred()
      const releaseActivation = deferred()
      const falseSaved = deferred()
      const events = []
      const writes = []
      const rows = new Map([
        [current, { ...selection }],
        [target, { ...selection, peer_id: target }],
      ])
      ExtensionParticipationModel.get = async (peerId) => {
        const snapshot = { ...rows.get(peerId) }
        snapshot.setEnabled = async (enabled) => {
          writes.push(enabled)
          rows.get(peerId).enabled = enabled
          if (!enabled) falseSaved.resolve()
          return { ...rows.get(peerId) }
        }
        return snapshot
      }
      ExtensionParticipationModel.list = async (peerId) => [
        await ExtensionParticipationModel.get(peerId),
      ]
      const runtime = new ExtensionManager({
        peerId: current,
        releases,
        moduleFederation: {
          registerRemotes() {},
          async loadRemote() {
            if (scenario === 'pending-load-disable') {
              entered.resolve()
              await releaseActivation.promise
            }
            return {
              async initialize() {
                events.push('initialize')
                entered.resolve()
                await releaseActivation.promise
              },
              activate() {
                events.push('activate')
              },
              deactivate() {
                events.push('deactivate')
              },
              dispose() {
                events.push('dispose')
              },
            }
          },
        },
      })
      const restore = runtime.startup(current)
      await entered.promise
      assert.deepEqual(writes, [], 'startup must not rewrite intent')
      let command
      if (scenario === 'disable-command' || scenario === 'pending-load-disable') {
        command = runtime.disable(selection.name, current)
        await falseSaved.promise
        assert.equal(runtime.isRunning(selection.name), false)
      } else if (scenario === 'external-disable') {
        rows.get(current).enabled = false
      } else if (scenario === 'external-pin') {
        rows.get(current).version = '1.2.0'
      } else {
        command = runtime.shutdown()
      }
      releaseActivation.resolve()
      await restore
      await command
      assert.equal(runtime.isRunning(selection.name), false, scenario)
      assert.deepEqual(
        events,
        scenario === 'pending-load-disable'
          ? ['dispose']
          : ['initialize', 'activate', 'deactivate', 'dispose'],
        scenario,
      )
      assert.deepEqual(
        writes,
        scenario === 'disable-command' || scenario === 'pending-load-disable' ? [false] : [],
        scenario,
      )
      assert.equal(rows.get(current).enabled, !scenario.includes('disable'), scenario)
      assert.equal(rows.get(current).version, scenario === 'external-pin' ? '1.2.0' : '1.10.0')
      assert.equal(rows.get(target).enabled, true)
      assert.equal(rows.get(target).version, '1.10.0')
      await runtime.shutdown()
    }
  } finally {
    ExtensionParticipationModel.get = originalGet
    ExtensionParticipationModel.list = originalList
  }
  assert.deepEqual(
    (await listAdvertisedExtensionManagementPeers()).map(({ id }) => id),
    [target, current],
  )
  assert.equal(requests.at(-1).url.searchParams.get('lease_expires_at'), 'gt.now')
  for (const command of [
    {
      action: 'select',
      extension: installed.name,
      distribution: 'python',
      version: installed.version,
    },
    { action: 'enable', extension: installed.name },
    { action: 'disable', extension: installed.name },
    { action: 'unselect', extension: installed.name },
    { action: 'patch_config', extension: installed.name, patch: { personal_access_token: secret } },
  ]) {
    assert.deepEqual(await manageExtensionOnPeer(target, command), installed)
    assert.ok(requests.at(-2).url.searchParams.getAll('id').includes(`eq.${target}`))
    assert.deepEqual(JSON.parse(requests.at(-1).body), command)
  }
  const native = {
    ...installed,
    distribution: 'kotlin_apk',
    supported_distributions: ['kotlin_apk'],
  }
  managementBody = { ...envelope, supported_distributions: ['kotlin_apk'], extensions: [native] }
  const nativeCommand = {
    action: 'select',
    extension: native.name,
    distribution: native.distribution,
    version: native.version,
  }
  assert.deepEqual(await manageExtensionOnPeer(target, nativeCommand), native)
  assert.deepEqual(JSON.parse(requests.at(-1).body), nativeCommand)
  managementStatus = 422
  managementBody = { detail: secret }
  await assert.rejects(
    manageExtensionOnPeer(target, { action: 'enable', extension: installed.name }),
    (error) => /HTTP 422/.test(error.message) && !JSON.stringify(error).includes(secret),
  )
  managementStatus = 200
  managementBody = { ...envelope, peer_id: secret }
  await assert.rejects(
    manageExtensionOnPeer(target, { action: 'enable', extension: installed.name }),
    (error) => !`${error.message}${JSON.stringify(error)}`.includes(secret),
  )
  dropManagement = true
  const before = requests.filter(({ url }) => url.pathname === '/manage').length
  await assert.rejects(
    manageExtensionOnPeer(target, { action: 'enable', extension: installed.name }),
    PeerOutcomeUnknown,
  )
  assert.equal(requests.filter(({ url }) => url.pathname === '/manage').length, before + 1)
  await assert.rejects(
    manageExtensionOnPeer('', { action: 'enable', extension: installed.name }),
    TypeError,
  )

  docBody = {
    name: installed.name,
    version: installed.version,
    state: 'yanked',
    sets: ['global', 'python', 'module-federation'].map((scope) => ({
      scope,
      entry_url: `https://docs.example.test/${scope}/#connect`,
      snapshot_id: 'a'.repeat(32),
      content_sha256: 'b'.repeat(64),
      snapshot_url: 'https://snapshot.example.test/',
      source_repository: 'https://example.test/source',
      source_revision: 'test',
      updated_at: '2026-01-01T00:00:00Z',
      etag: 'test',
    })),
  }
  const readDocs = () => getExtensionDocumentation(origin, installed.name, installed.version)
  assert.deepEqual(
    await readDocs(),
    docBody.sets.map(({ scope, entry_url }) => ({ scope, entry_url })),
  )
  assert.equal(
    requests.at(-1).url.pathname,
    '/v1/extensions/inkcre/memos/releases/0.2.0/documentation',
  )
  assert.equal(requests.at(-1).headers.authorization, undefined)
  for (const unsafe of ['javascript:alert(1)', `https://user:${secret}@docs.example.test/`]) {
    docBody.sets[0].entry_url = unsafe
    await assert.rejects(readDocs(), RegistryDocumentationError)
  }
  docBody.sets = []
  assert.deepEqual(await readDocs(), [])
  docBody.version = '0.3.0'
  await assert.rejects(readDocs(), RegistryDocumentationError)
  docStatus = 404
  assert.equal(await readDocs(), null)
  docStatus = 503
  await assert.rejects(readDocs(), RegistryDocumentationError)
  dropDocumentation = true
  await assert.rejects(readDocs(), RegistryDocumentationError)
  console.log('Built Runtime / real Core SDK HTTP boundaries passed.')
} finally {
  server.closeAllConnections()
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  )
}
