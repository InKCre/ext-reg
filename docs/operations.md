# Operations

## Cutover Boundary

The native schema is a clean initial schema, not an in-place migration from the
rejected generic target database. The authorized cutover created fresh
`inkcre-extension-registry-production-v2` D1 and R2 resources and froze their
bindings in `wrangler.jsonc`. After production and cross-Peer acceptance, the
explicitly authorized rollback window ended and the pre-cutover
`inkcre-extension-registry-production` D1/R2 pair was permanently removed.

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

The human Preview covers only the read-only Extension-list page. Registry APIs,
publisher flows, Python Simple, Module Federation, installation, and runtime
behavior remain the local real-Worker black-box contract.

Every pull request runs secret-free checks and produces a one-day Actions
artifact containing one bounded `index.html` rendered from the checked review
fixture. GitHub requires maintainer approval before any external fork
contributor's workflows start. Approval does not grant credentials: fork PRs
stop after checks and artifact evidence and never receive a remote Preview.

For a same-repository PR, `.github/workflows/pages-preview.yml` runs as a
trusted `workflow_run` controller selected from protected `main`. It verifies
the successful `Registry checks` run, one open PR targeting `main`, same-repo
origin, and exact current head SHA before entering the protected `preview`
Environment. The controller uses official GitHub artifact transfer, accepts
only the single regular document within its size bound, and copies it into a
fresh deploy directory. It does not parse or sanitize candidate HTML/CSS.

Protected-main code adds `preview.json` with the PR/source identity and
`_headers` with noindex, no-store, CSP, nosniff, and no-referrer. Wrangler Direct
Upload publishes that directory to the single project
`inkcre-extension-registry-ui-preview` on branch
`preview/ext-reg/pr-<number>`. Links in the static document point to public
production reads at `https://registry.inkcre.dev`; the Pages origin never
pretends to host candidate Registry APIs.

Preview authority is deliberately narrow:

- repository variable `CLOUDFLARE_ACCOUNT_ID` identifies the account;
- repository variable `REGISTRY_UI_PREVIEW_PAGES_PROJECT` must equal
  `inkcre-extension-registry-ui-preview`;
- the protected `preview` Environment owns
  `CLOUDFLARE_PAGES_API_TOKEN`, scoped only to account-level Pages Write;
- the project has no Git provider, custom domain, Functions, Worker, D1, R2, or
  other binding;
- production uses a separate Environment and token.

Closing an internal PR runs the trusted default-branch cleanup without checking
out candidate code. It deploys the checked-in tombstone to the same branch,
verifies the stable alias, and uses Wrangler's Pages deployment commands to
delete older deployments for only that exact project/branch. Cloudflare retains
the latest tombstone because the latest branch deployment cannot be deleted.
The one-day Actions artifact expires through GitHub's normal retention policy.

The workflow that introduces the trusted controller cannot preview itself;
`workflow_run` must already exist on the default branch. After merge, use one
bounded internal canary to prove the Preview Environment branch rule, exact-head
update, close cleanup, and actual Free-plan usage. If Direct Upload consumes an
unexpected paid/build quota or the Environment/controller boundary fails, turn
off remote delivery and retain the one-day artifact. Do not create another
Preview topology.

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
  -> after explicit acceptance, empty and permanently delete the old D1/R2 pair
```

No old target rows, generic blobs, credentials, or demo Releases are migrated.
The old resources were deleted only after the rollback window ended with
explicit authorization.

## Delivery, Failure, And Rollback

CI builds and tests the Registry/Worker from frozen Python and Node dependency
graphs. The production workflow rechecks that the authorized SHA is still
current `main`, verifies the frozen `-v2` bindings, and only then migrates and
deploys. Do not deploy from a controller checkout, moved branch, or mutable
package artifact.

During the bounded cutover window, rollback restored the old Worker bindings and
verified Worker revision while the old D1/R2 resources existed. That window is
now closed: rollback remains available only within the native-v2 data plane by
deploying a previously verified compatible Worker Version. The deleted generic
target data plane cannot be restored. R2 staging garbage is never public without
D1 authority and may be removed later by a bounded lifecycle rule.

After cutover verify `/livez`, exact Release descriptors, Simple 1.1 HTML/JSON,
wheel plus `.metadata`, MF manifest/assets, CORS/cache/ETag, identical retry,
conflict, yank/unyank, and blocked-read behavior. Record source SHA, workflow
run, resource identifiers, migration state, and read-after-write observations
without raw credentials.
