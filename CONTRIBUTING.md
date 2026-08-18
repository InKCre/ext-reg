# Contributing

Use Python 3.13, Node 22, uv 0.12.3, and pnpm 11.11.0. Install frozen
dependencies and run the repository contract before opening a pull request:

```bash
uv sync --frozen
pnpm install --frozen-lockfile
pnpm check
```

`pnpm check` verifies generated contracts, formatting, lint, types, focused
tests, the Registry package, and the real Pyodide Worker build. To update an executable
contract intentionally:

```bash
pnpm contracts:generate
pnpm check
```

Pull requests target protected `main`, preserve linear history, and include the
scope, verification evidence, risk, and rollback. CI and previews may publish
ephemeral evidence, but canonical packages and production deployment only come
from an exact successful current-`main` revision. Do not commit credentials,
local Wrangler state, generated dependency directories, or unrelated changes.

Registry, Toolkit publication and Cloudflare production changes are separate
privileged operations. Extension publishers install the independent
`inkcre-extension-toolkit[cli]` distribution, prepare typed associations with
`inkcre-ext prepare-release`, use `uv publish`/Twine for wheels or
`inkcre-ext upload-module-federation` for a native Remote snapshot, and publish
the Release explicitly. Source revision and build identity should accompany the
prepare request.
