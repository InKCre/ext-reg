import { execFileSync } from 'node:child_process'
import {
  cpSync,
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

// The SDK has no published build yet. Build its pinned source with this repository's
// frozen tools and dependencies, without installing the producer workspace or editing the store.
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
    run('git', ['checkout', '--quiet', 'FETCH_HEAD', '--', 'packages/core'])
    const source = join(checkout, 'packages/core')
    // Build outside node_modules: Node 22 does not strip types from configs inside it.
    symlinkSync(dirname(dirname(installed)), join(source, 'node_modules'), 'dir')
    symlinkSync(join(root, 'node_modules'), join(checkout, 'packages/node_modules'), 'dir')
    run(join(root, 'node_modules/.bin/tsdown'), [], source)
    mkdirSync(output, { recursive: true })
    for (const entry of ['package.json', 'dist']) {
      cpSync(join(source, entry), join(output, entry), { recursive: true })
    }
    const dependencies = join(output, 'node_modules')
    if (lstatSync(dependencies, { throwIfNoEntry: false })) unlinkSync(dependencies)
    // SDK runtime dependencies live beside the scoped pnpm package. Build tools resolve
    // from the enclosing Runtime workspace node_modules, all under this repository's lock.
    symlinkSync(dirname(dirname(installed)), dependencies, 'dir')
  } finally {
    rmSync(checkout, { recursive: true, force: true })
  }
  unlinkSync(dependency)
  symlinkSync(output, dependency, 'dir')
}
if (
  realpathSync(dependency) !== output ||
  !existsSync(join(output, 'dist/index.d.ts')) ||
  !existsSync(join(output, 'dist/index.js'))
) {
  throw new Error('Core SDK preparation did not resolve to the isolated real build.')
}
console.log(`Core SDK ready from client-web ${revision}.`)
