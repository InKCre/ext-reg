# Operations

## Cutover Boundary

The native schema is a clean initial schema, not an in-place migration from the
rejected generic target database. The later authorized cutover must create a
new D1 database and R2 bucket, seed a newly hashed namespace credential, update
the Worker bindings, deploy, and smoke the native paths as one rollback unit.
The currently configured remote identifiers remain unchanged until that
separate Cloudflare-mutation authorization.

The production workflow is temporarily a non-mutating handoff gate. It is
manual, takes an exact current-main SHA, installs frozen dependencies, runs the
full repository contract, and records that remote mutation is disabled. It has
no Cloudflare credentials or migration/deploy steps. The protected
`production` environment remains in place so the later delivery handshake can
restore mutation only after exact new D1/R2 bindings have been frozen. Never
place raw publisher tokens in logs, task evidence, D1, or workflow summaries.

The frozen public origin and Worker Custom Domain are both
`https://registry.inkcre.dev`. A later authorized deploy may create the Custom
Domain and certificate; committing this configuration does not perform that
remote mutation.

## Local Worker Black Box

Use an isolated local Wrangler state or a clean checkout:

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

The fixed token above is local test data only. The smoke sends a real
`uv publish`, installs the exact wheel back through the Simple API, loads its
native entry point, and reads Core Metadata. It also prepares, uploads, and
publishes an MF snapshot before proving its absolute public path through the
actual Worker/R2 seam. Unit black boxes additionally cover idempotency,
conflict, yanking, bounds, and operator blocking.

## Authorized Provisioning Outline

Resolve exact new resource names during the delivery handshake, then execute
the equivalent of:

```text
create new D1 + private R2
  -> write exact bindings
  -> bind registry.inkcre.dev as Custom Domain and PUBLIC_ORIGIN
  -> apply 0001_registry.sql to empty D1
  -> seed namespace + hashed rotated credential
  -> deploy exact verified current-main Worker
  -> read-after-write Python and MF smoke
  -> switch/verify public origin
  -> retain old resources for the bounded rollback window
```

No old target rows, generic blobs, credentials, or demo Releases are migrated.
Deleting old resources occurs only after the rollback window and needs its own
explicit authorization.

## Delivery, Failure, And Rollback

CI builds and tests the Registry/Worker from frozen Python and Node dependency
graphs. The current handoff workflow rechecks that the authorized SHA is still
current `main` and runs the exact source contract, but cannot mutate remote
state. A later separately reviewed workflow may restore migration and deploy
only after the delivery handshake has frozen new resource bindings. Do not
deploy from a controller checkout, moved branch, or mutable package artifact.

Rollback restores the old Worker bindings and verified Worker revision while
the old D1/R2 resources still exist. New native D1/R2 resources stay intact for
diagnosis. R2 staging garbage is never public without D1 authority and may be
removed later by a bounded lifecycle rule.

After cutover verify `/livez`, exact Release descriptors, Simple 1.1 HTML/JSON,
wheel plus `.metadata`, MF manifest/assets, CORS/cache/ETag, identical retry,
conflict, yank/unyank, and blocked-read behavior. Record source SHA, workflow
run, resource identifiers, migration state, and read-after-write observations
without raw credentials.
