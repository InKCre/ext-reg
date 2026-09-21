import { execFileSync } from 'node:child_process'
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  rmSync,
  symlinkSync,
  unlinkSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// The SDK has no published build yet. Its pinned Git package supplies locked dependencies;
// build its real artifact with the producer's lockfile, without editing pnpm's shared store.
const root = dirname(fileURLToPath(import.meta.url))
const manifest = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'))
const revision = /^github:InKCre\/client-web#([a-f0-9]{40})&path:\/packages\/core$/.exec(
  manifest.devDependencies['@inkcre/core'],
)?.[1]
if (!revision)
  throw new Error('Core SDK development dependency must pin one full client-web Git revision.')
const dependency = join(root, 'node_modules/@inkcre/core')
const installed = realpathSync(dependency)
const output = join(root, `node_modules/.inkcre-core-sdk-${revision}`)
if (
  !lstatSync(dependency).isSymbolicLink() ||
  (existsSync(output) && lstatSync(output).isSymbolicLink())
) {
  throw new Error(
    'SDK preparation requires a workspace dependency link and a private build directory.',
  )
}
if (installed !== output) {
  const checkout = mkdtempSync(join(tmpdir(), 'inkcre-core-sdk-'))
  const run = (command, args, cwd = checkout) =>
    execFileSync(command, args, { cwd, stdio: 'inherit' })
  try {
    run('git', ['init', '--quiet'])
    run('git', [
      'fetch',
      '--quiet',
      '--depth=1',
      'https://github.com/InKCre/client-web.git',
      revision,
    ])
    run('git', ['checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    run('pnpm', ['--filter', '@inkcre/core...', 'install', '--frozen-lockfile', '--ignore-scripts'])
    run('pnpm', ['--filter', '@inkcre/core', 'build'])
    run('pnpm', ['pack', '--pack-destination', checkout], join(checkout, 'packages/core'))
    const sdk = JSON.parse(readFileSync(join(checkout, 'packages/core/package.json'), 'utf8'))
    mkdirSync(output, { recursive: true })
    run('tar', [
      '-xzf',
      join(checkout, `inkcre-core-${sdk.version}.tgz`),
      '--strip-components=1',
      '-C',
      output,
    ])
  } finally {
    rmSync(checkout, { recursive: true, force: true })
  }
  const dependencies = join(output, 'node_modules')
  if (lstatSync(dependencies, { throwIfNoEntry: false })) unlinkSync(dependencies)
  // pnpm places dependencies beside this scoped package, in its virtual node_modules.
  symlinkSync(dirname(dirname(installed)), dependencies, 'dir')
  unlinkSync(dependency)
  symlinkSync(output, dependency, 'dir')
}
if (realpathSync(dependency) !== output || !existsSync(join(output, 'dist/index.d.ts'))) {
  throw new Error('Core SDK preparation did not resolve to the isolated real build.')
}
console.log(`Core SDK ready from client-web ${revision}.`)
