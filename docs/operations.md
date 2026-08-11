# Operations

## Cutover Boundary

The native schema is a clean initial schema, not an in-place migration from the
rejected generic target database. The authorized cutover created fresh
`inkcre-extension-registry-production-v2` D1 and R2 resources and froze their
bindings in `wrangler.jsonc`. The pre-cutover same-named resources remain
untouched as the bounded rollback data plane.

The production workflow is manual, takes an exact current-main SHA, rejects a
moved branch or unexpected binding identity, installs frozen dependencies,
runs the full repository contract, applies only checked-in D1 migrations,
deploys the exact Worker, and smokes anonymous public reads. It never creates
or deletes Cloudflare resources. The protected `production` environment owns
the deploy credential boundary. Never place raw publisher tokens in logs, task
evidence, D1, or workflow summaries.

The public origin and Worker Custom Domain are both
`https://registry.inkcre.dev`.

## Pull Request Previews

Registry checks can upload an exact, tested PR head as a Cloudflare Worker
Version with the stable alias `pr-<number>`. The preview uses the separate
Worker name `inkcre-extension-registry-preview`, explicit Preview URLs, and
dedicated preview D1/R2 bindings. It never inherits the production binding
names or the `registry.inkcre.dev` Custom Domain. The shared preview database
contains only an idempotent `inkcre/preview` catalog fixture and no publisher
credential.

The deploy job runs only for same-repository PRs after the repository contract
passes. Before enabling it, create the following repository variables:

- `CLOUDFLARE_ACCOUNT_ID`
- `REGISTRY_PREVIEW_D1_DATABASE_ID`
- `REGISTRY_PREVIEW_D1_DATABASE_NAME`
- `REGISTRY_PREVIEW_R2_BUCKET_NAME`
- `REGISTRY_PREVIEW_WORKERS_SUBDOMAIN` (the account subdomain without
  `.workers.dev`)

Store `CLOUDFLARE_API_TOKEN` as an organization Actions secret with selected
repository access that includes `ext-reg`, and restrict it to the target account
with Workers Scripts Write, D1 Write, and Workers R2 Storage Write. Wrangler's
first Worker deploy validates the named R2 bucket through an endpoint that
requires R2 Storage Write even though the workflow never creates, modifies, or
deletes that bucket. Runtime object access still comes from the Worker binding.
Until every variable exists, CI reports the missing preview contract and skips
deployment without touching Cloudflare. The preview D1 and R2 are provisioned
out of band. If the dedicated preview Worker service does not yet exist, the
workflow bootstraps that service once from the fail-closed preview config; it
then applies migrations only to the explicit preview D1 and exposes each exact
checked Worker Version through its PR alias. The preview config contains no
production route or Custom Domain.

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

The production delivery executes the equivalent of:

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
graphs. The production workflow rechecks that the authorized SHA is still
current `main`, verifies the frozen `-v2` bindings, and only then migrates and
deploys. Do not deploy from a controller checkout, moved branch, or mutable
package artifact.

Rollback restores the old Worker bindings and verified Worker revision while
the old D1/R2 resources still exist. New native D1/R2 resources stay intact for
diagnosis. R2 staging garbage is never public without D1 authority and may be
removed later by a bounded lifecycle rule.

After cutover verify `/livez`, exact Release descriptors, Simple 1.1 HTML/JSON,
wheel plus `.metadata`, MF manifest/assets, CORS/cache/ETag, identical retry,
conflict, yank/unyank, and blocked-read behavior. Record source SHA, workflow
run, resource identifiers, migration state, and read-after-write observations
without raw credentials.
