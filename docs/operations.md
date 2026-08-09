# Operations

## Production Resources

- Worker: `inkcre-extension-registry`
- D1: `inkcre-extension-registry-production`
- private R2 bucket: `inkcre-extension-registry-production`
- public origin: the Worker deployment URL recorded after delivery

`wrangler.jsonc` contains non-secret bindings and the real D1 identifier.
GitHub's `production` environment owns `CLOUDFLARE_API_TOKEN` and
`CLOUDFLARE_ACCOUNT_ID`. Workflow permissions remain read-only except the
bounded package/release job.

## Local Worker Black Box

Use an isolated local Wrangler state or a clean checkout:

```bash
pnpm exec wrangler d1 migrations apply DB --local --config wrangler.jsonc
pnpm exec wrangler d1 execute DB --local --config wrangler.jsonc \
  --file tests/fixtures/local-seed.sql
uv run pywrangler dev --port 8791
uv run python scripts/worker_smoke.py \
  --registry-url http://127.0.0.1:8791 \
  --token inkcre-local-publisher-token
```

The fixed token above is local test data only.

## Provisioning And Migration

Create D1 and R2 once with Wrangler, write the returned D1 ID to
`wrangler.jsonc`, then apply migrations remotely. Migrations are forward-only
and append-only after merge:

```bash
pnpm exec wrangler d1 create inkcre-extension-registry-production
pnpm exec wrangler r2 bucket create inkcre-extension-registry-production
pnpm exec wrangler d1 migrations apply DB --remote --config wrangler.jsonc
```

Seed `inkcre` plus hashed, separately generated peer credentials using the D1
operator command. Raw tokens go directly to the relevant peer repository's
`INKCRE_EXTENSION_REGISTRY_TOKEN` secret and never to D1, logs, task files, or
workflow summaries. Rotation creates a new credential, updates the consumer
secret, proves publication, then disables the old credential.

## Delivery And Rollback

CI builds the Python/Web packages and Worker from frozen dependencies. Release
and production workflows re-check that their source SHA is still current
`main`. Production applies D1 migrations before deploying the exact Worker.

Rollback deploys a previously verified Worker revision. D1 is not rolled back;
new code must remain backward-compatible with applied migrations. R2 objects
and published target associations are immutable. A bad Extension Version is
yanked; a harmful artifact association is operator-blocked. Neither operation
silently changes an existing deployment's installed/enabled/running state.

After deployment, verify `/livez`, anonymous catalog access, authenticated
publication, exact digest manifest/file delivery, CORS/cache headers, and byte
hash. Record the source SHA, workflow run, Worker version, D1 migration state,
and smoke target digest.
