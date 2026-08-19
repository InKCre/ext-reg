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
