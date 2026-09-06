import { readFileSync } from 'node:fs'
import * as sass from 'sass'
const output = sass.compile('web/registry.scss', {
  importers: [new sass.NodePackageImporter(process.cwd())],
  style: 'compressed',
})
const committed = readFileSync('src/inkcre_extension_registry/service/static/registry.css', 'utf8')
if (output.css.trim() !== committed.trim()) {
  throw new Error('Registry CSS is stale. Run pnpm web:build and commit the generated stylesheet.')
}
console.log('Registry styles match the pinned @inkcre/ui-web package and local Sass.')
