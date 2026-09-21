import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { once } from 'node:events'
import { configStore, PeerManager, PeerOutcomeUnknown } from '@inkcre/core'
import {
  EXTENSION_MANAGEMENT_CAPABILITY,
  getExtensionDocumentation,
  listAdvertisedExtensionManagementPeers,
  manageExtensionOnPeer,
  RegistryDocumentationError,
} from './dist/index.js'

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
