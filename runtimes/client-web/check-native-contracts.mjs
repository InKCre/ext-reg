import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { RegistryReleaseError, RegistryReleaseReader } from './dist/index.js'
import { zNativePrepareReleaseRequest, zNativeReleaseRecord } from './src/generated/zod.gen.ts'

const vectors = JSON.parse(
  await readFile(new URL('../../scripts/fixtures/native-contracts.json', import.meta.url), 'utf8'),
)
for (const [kind, schema] of [
  ['release', zNativeReleaseRecord],
  ['prepare', zNativePrepareReleaseRequest],
]) {
  for (const vector of vectors[kind]) {
    assert.equal(schema.safeParse(vector.payload).success, vector.valid, `${kind}: ${vector.id}`)
  }
}
let payload
const reader = new RegistryReleaseReader({
  registryOrigin: 'https://registry.example.test',
  hostSdk: { name: '@inkcre/core', version: '0.4.2' },
  fetch: async () => Response.json(payload),
})
for (const vector of vectors.release) {
  payload = vector.payload
  const read = () => reader.getRelease('inkcre/example', '1.0.0', true, payload.distribution)
  if (vector.valid) {
    assert.equal((await read()).distribution, payload.distribution, vector.id)
  } else {
    await assert.rejects(read, RegistryReleaseError, vector.id)
  }
}
payload = { ...vectors.release[0].payload, version: '2.0.0' }
await assert.rejects(() => reader.getRelease('inkcre/example', '1.0.0', true, 'python'))
payload = { ...vectors.release[0].payload, state: 'blocked' }
await assert.rejects(() => reader.getRelease('inkcre/example', '1.0.0', false, 'python'))
payload = { ...vectors.release[0].payload, state: 'yanked' }
await assert.rejects(() => reader.getRelease('inkcre/example', '1.0.0', true, 'python'))
assert.equal((await reader.getRelease('inkcre/example', '1.0.0', false, 'python')).state, 'yanked')
payload = {
  ...vectors.release[1].payload,
  module_federation: {
    ...vectors.release[1].payload.module_federation,
    host_sdk_version: '>=0.5.0',
  },
}
await assert.rejects(() => reader.get('inkcre/example', '1.0.0', true))
console.log('Native contract vectors through the built Web Runtime passed.')
