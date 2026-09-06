# Local Development

Install frozen Python and Node dependencies and run the full contract:

```bash
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
pnpm check
```

For the real local Worker seam, use isolated Wrangler state or a clean checkout:

```bash
pnpm exec wrangler d1 migrations apply DB --local --config wrangler.jsonc
pnpm build
UV_FIND_LINKS="$PWD/dist" pdm run pywrangler dev --port 8791 \
  --var PUBLIC_ORIGIN:http://127.0.0.1:8791
```

`.wrangler/`, virtual environments, `python_modules/`, dependency directories,
build output, and secrets are local state and must remain uncommitted.

## Package release intent

The Python Toolkit and Core Runtime use the pinned Changie configuration and
their own changelogs. The Web Runtime uses Changesets. A merge to protected
`main` may only create or update the Web Version PR; package assets are produced
later from the Version PR's merged current-main revision in the protected
`production` environment.

The package workflow skips an already existing package tag, so a rerun can
finish a partially completed three-package release without replacing an
existing Release. Registry Worker deployment remains a separate workflow.

## Registry Web development

Use Node 22 as declared by `package.json`; newer Node majors may not support the
Wasm stack-switching flag required by the locked Pyodide toolchain. Registry
consumes only the public Sass exports of `@inkcre/ui-web`. pnpm installs
`packages/web` from the public `InKCre/ui` Git repository at commit
`4eceec4c60345a52a08545555ebce9ab95053beb` (release `@inkcre/ui-web@1.4.0`).
The immutable commit and subdirectory are pinned in the manifest and lockfile;
no GitHub Packages credential or additional release workflow is needed.
The source package is suitable for Sass consumption; its Vue runtime/dist
exports are not used by Registry. To upgrade, select the next protected-main
release commit, update the dependency, and rebuild/review the CSS.

Edit `web/registry.scss`, then run `pnpm web:build`. Generated CSS is committed and
verified by `pnpm web:check`. Templates and browser JavaScript live under
`src/inkcre_extension_registry/service/`. After changing packaged files, rebuild
with `pnpm build` and restart the local Worker using `UV_FIND_LINKS="$PWD/dist"` so
the Worker consumes the current local wheel. Do not test an older installed wheel.

Open `/`, `/explore/<namespace>/<name>`, and `/publish` on the local Worker. Apply
credentials and fixtures only to isolated local D1; use the existing native APIs
for prepare/upload/publish acceptance. Verify search, exact version selection,
empty results, namespace scoping, upload readiness, publish/withdraw/restore,
reconnection, keyboard navigation, and narrow/light/dark pages. The task packet
records the actual black-box evidence; no new mock-based browser suite is required.
