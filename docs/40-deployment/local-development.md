# Local Development

Install frozen Python and Node dependencies and run the full contract:

```bash
uv sync --frozen
pnpm install --frozen-lockfile
pnpm check
```

For the real local Worker seam, use isolated Wrangler state or a clean checkout:

```bash
pnpm exec wrangler d1 migrations apply DB --local --config wrangler.jsonc
pnpm exec wrangler d1 execute DB --local --config wrangler.jsonc \
  --file tests/fixtures/local-seed.sql
uv run pywrangler dev --port 8791 \
  --var PUBLIC_ORIGIN:http://127.0.0.1:8791
uv run python scripts/worker_smoke.py \
  --registry-url http://127.0.0.1:8791 \
  --token inkcre-local-publisher-token
```

The fixed token is local test data only. The smoke publishes and reinstalls a
wheel through the Simple API, loads its entry point and metadata, and proves a
Module Federation snapshot through the Worker/R2 boundary. `.wrangler/`,
virtual environments, `python_modules/`, dependency directories, build output,
and secrets are local state and must remain uncommitted.
