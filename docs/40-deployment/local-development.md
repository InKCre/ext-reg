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
pdm run pywrangler dev --port 8791 \
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
