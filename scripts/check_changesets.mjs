import { readFile, readdir } from 'node:fs/promises'
import parse from '@changesets/parse'

const directory = new URL('../.changeset/', import.meta.url)
const files = (await readdir(directory)).filter(
  (name) => name.endsWith('.md') && name !== 'README.md',
)

for (const file of files) {
  const changeset = parse(await readFile(new URL(file, directory), 'utf8'))
  for (const release of changeset.releases) {
    if (release.name !== '@inkcre/extension-runtime-client-web') {
      throw new Error(`${file}: Changesets cannot release Python package ${release.name}`)
    }
  }
}
