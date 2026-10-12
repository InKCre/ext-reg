import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { once } from 'node:events'
import { readFile } from 'node:fs/promises'
import { satisfies } from 'semver'
import { configStore, PeerManager, PeerOutcomeUnknown } from '@inkcre/core'
import {
  EXTENSION_MANAGEMENT_CAPABILITY,
  ExtensionManager,
  NativeDistributionSupportChangeError,
  getExtensionDocumentation,
  listAdvertisedExtensionManagementPeers,
  manageExtensionOnPeer,
  preferredPublishedRelease,
  RegistryDocumentationError,
  RegistryReleaseReader,
  sortPublishedReleases,
} from './dist/index.js'

const coreRequirement = JSON.parse(await readFile(new URL('./package.json', import.meta.url)))
  .peerDependencies['@inkcre/core']
assert.equal(
  satisfies('0.3.0', coreRequirement),
  false,
  'Older SDKs do not provide atomic version changes',
)
assert.equal(satisfies('0.3.1', coreRequirement), true)
assert.equal(satisfies('0.4.0', coreRequirement), false)

// Exercise the built package and real SDK over HTTP, without a deployment or real credentials.
const target = '11111111-1111-4111-8111-111111111111'
const current = '22222222-2222-4222-8222-222222222222'
const secret = 'boundary-check-secret'
const installed = {
  name: 'inkcre/memos',
  version: '0.2.0',
  enabled: [target],
  nickname: 'Memos',
  config: {},
  config_schema: null,
}
let origin
let managementStatus = 200
let managementBody = installed
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
    module_federation: null,
    python: null,
  },
  {
    name: 'inkcre/catalog',
    nickname: 'Catalog check',
    version: '1.10.0',
    state: 'published',
    module_federation: null,
    python: null,
  },
  {
    name: 'inkcre/catalog',
    nickname: 'Catalog check',
    version: '1.2.0',
    state: 'published',
    module_federation: null,
    python: null,
  },
]
const supportReleases = new Map([
  [
    '1.0.0',
    {
      name: 'inkcre/support',
      nickname: 'Support',
      version: '1.0.0',
      state: 'published',
      python: {
        project: 'inkcre-support',
        simple_url: '/simple/inkcre-support/',
        host_sdk: 'core-py',
        host_sdk_version: '^1.0.0',
        entry_point: {
          group: 'inkcre.core.extensions',
          name: 'support',
          object: 'support:Extension',
        },
      },
      module_federation: {
        manifest_url: '/extensions/inkcre/support/1.0.0/module-federation/mf-manifest.json',
        host_sdk: '@inkcre/core',
        host_sdk_version: '^1.0.0',
      },
    },
  ],
])
supportReleases.set('2.0.0', {
  ...supportReleases.get('1.0.0'),
  version: '2.0.0',
  module_federation: null,
})
let installedSupport = null
let supportWrites = 0
let previousReleaseStatus = 200
let dropPreviousRelease = false
let changeDuringPreflight = false
const supportRow = (version) => ({
  name: 'inkcre/support',
  nickname: 'Support',
  version,
  enabled: [],
  config: {},
  config_schema: null,
})
const requests = []
const server = createServer(async (request, response) => {
  const url = new URL(request.url, origin)
  const chunks = []
  for await (const chunk of request) chunks.push(chunk)
  requests.push({ url, headers: request.headers, body: Buffer.concat(chunks).toString() })
  response.setHeader('Content-Type', 'application/json')
  if (url.pathname === '/extensions') {
    if (request.method === 'POST') {
      supportWrites++
      installedSupport = { ...JSON.parse(Buffer.concat(chunks).toString()), enabled: [] }
      response.end(JSON.stringify(installedSupport))
    } else if (request.method === 'PATCH') {
      supportWrites++
      const matches =
        installedSupport !== null &&
        installedSupport.enabled.length === 0 &&
        url.searchParams.get('version') === `eq.${installedSupport.version}`
      if (matches)
        installedSupport = { ...installedSupport, ...JSON.parse(Buffer.concat(chunks).toString()) }
      response.end(JSON.stringify(matches ? [installedSupport] : []))
    } else response.end(JSON.stringify(installedSupport === null ? [] : [installedSupport]))
  } else if (url.pathname.startsWith('/v1/extensions/inkcre/support/releases/')) {
    const version = url.pathname.split('/').at(-1)
    if (version === '1.0.0') {
      if (dropPreviousRelease) return request.socket.destroy()
      response.statusCode = previousReleaseStatus
      if (changeDuringPreflight) installedSupport = supportRow('3.0.0')
    }
    response.end(JSON.stringify(supportReleases.get(version)))
  } else if (url.pathname === '/peers') {
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
  } else if (url.pathname === '/v1/extensions') {
    response.end(JSON.stringify([{ name: 'inkcre/catalog', nickname: 'Catalog check' }]))
  } else if (url.pathname === '/v1/extensions/inkcre/catalog') {
    response.end(
      JSON.stringify({
        name: 'inkcre/catalog',
        nickname: 'Catalog check',
        releases: catalogReleases,
      }),
    )
  } else if (url.pathname.startsWith('/v1/extensions/inkcre/catalog/releases/')) {
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
  await assert.rejects(
    releases.get('inkcre/catalog', '1.10.0', true),
    /no Module Federation Distribution/,
  )
  assert.deepEqual(
    (await listAdvertisedExtensionManagementPeers()).map(({ id }) => id),
    [target, current],
  )
  assert.equal(requests.at(-1).url.searchParams.get('lease_expires_at'), 'gt.now')
  for (const command of [
    { action: 'install', extension: installed.name, version: installed.version },
    { action: 'enable', extension: installed.name },
    { action: 'disable', extension: installed.name },
    { action: 'patch_config', extension: installed.name, patch: { personal_access_token: secret } },
  ]) {
    assert.deepEqual(await manageExtensionOnPeer(target, command), installed)
    assert.ok(requests.at(-2).url.searchParams.getAll('id').includes(`eq.${target}`))
    assert.deepEqual(JSON.parse(requests.at(-1).body), command)
  }
  managementStatus = 422
  managementBody = { detail: secret }
  await assert.rejects(
    manageExtensionOnPeer(target, { action: 'enable', extension: installed.name }),
    (error) => /HTTP 422/.test(error.message) && !JSON.stringify(error).includes(secret),
  )
  managementStatus = 200
  managementBody = { ...installed, nickname: { [secret]: true } }
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
  const manager = new ExtensionManager({
    releases,
    moduleFederation: {
      registerRemotes() {
        throw new Error('Install must not load MF')
      },
      loadRemote() {
        throw new Error('Install must not load MF')
      },
    },
  })
  assert.equal(
    (await manager.install({ name: 'inkcre/support', version: '2.0.0' })).version,
    '2.0.0',
  )
  assert.equal(supportWrites, 1, 'Python-only installation is a deployment choice')
  await assert.rejects(manager.install({ name: 'inkcre/support', version: '1.0.0' }))
  assert.equal(
    installedSupport.version,
    '2.0.0',
    'Install cannot silently replace the exact version',
  )
  installedSupport = supportRow('1.0.0')
  supportWrites = 0
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0'), (error) => {
    assert.ok(error instanceof NativeDistributionSupportChangeError)
    assert.equal(error.reason, 'reduced')
    assert.equal(error.installedVersion, '1.0.0')
    assert.deepEqual(error.removedFormats, ['module_federation'])
    return true
  })
  assert.equal(supportWrites, 0)
  await assert.rejects(
    manager.changeVersion('inkcre/support', '2.0.0', { allowSupportChange: true }),
    TypeError,
  )
  const confirmation = { expectedInstalledVersion: '1.0.0', allowSupportChange: true }
  assert.equal(
    (await manager.changeVersion('inkcre/support', '2.0.0', confirmation)).version,
    '2.0.0',
  )
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0', confirmation))
  assert.equal(supportWrites, 1, 'A stale confirmation cannot mutate a different installed version')
  installedSupport = { ...supportRow('1.0.0'), enabled: [target] }
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0', confirmation))
  assert.equal(supportWrites, 1, 'All Peers must be disabled before a version change')
  for (const status of [404, 451]) {
    installedSupport = supportRow('1.0.0')
    previousReleaseStatus = status
    await assert.rejects(
      manager.changeVersion('inkcre/support', '2.0.0'),
      (error) =>
        error instanceof NativeDistributionSupportChangeError && error.reason === 'unavailable',
    )
    assert.equal(
      (await manager.changeVersion('inkcre/support', '2.0.0', confirmation)).version,
      '2.0.0',
    )
  }
  installedSupport = supportRow('1.0.0')
  const beforeTemporaryFailure = supportWrites
  previousReleaseStatus = 503
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0', confirmation))
  previousReleaseStatus = 200
  dropPreviousRelease = true
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0', confirmation))
  dropPreviousRelease = false
  assert.equal(
    supportWrites,
    beforeTemporaryFailure,
    'Temporary failures cannot authorize skipping the check',
  )
  changeDuringPreflight = true
  await assert.rejects(manager.changeVersion('inkcre/support', '2.0.0', confirmation))
  changeDuringPreflight = false
  assert.equal(
    installedSupport.version,
    '3.0.0',
    'Atomic update preserves a concurrent version change',
  )

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
