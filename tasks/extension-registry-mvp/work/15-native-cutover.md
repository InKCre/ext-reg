# Native Distribution Cutover

## Objective

Replace the production-proven generic target/binding architecture with the
accepted native Python and Module Federation Registry model across `ext-reg`,
`core-py`, and `client-web`, then execute a clean public-demo reset and cutover.

## Authorization Boundary

- Accepted: task-packet maintenance, read-only investigation, local PoCs, local
  code changes in all three repositories, local tests/builds, and preparation of
  exact reset/deployment procedures.
- Accepted in product scope: complete reset of Registry D1/R2 and exactly the
  three deployment Extension-state relations during the later public-demo
  cutover.
- Authorized on 2026-08-11: commits, pushes, and new unmerged PRs for the three
  reviewed native-cutover branches, including the read-only Registry catalog
  and canonical `registry.inkcre.dev` configuration.
- Authorized on 2026-08-11 by Sir's explicit `开始`: execute the previously
  presented ordered public-demo cutover, including production Registry D1/R2
  provisioning and binding, Registry publisher credentials, publication,
  sequential Ready/merge of `ext-reg#5`, `core-py#50`, and `client-web#63`, the
  exact Core-image Web contract synchronization commit/push, the clean reset of
  only Registry data and the three superseded deployment Extension-state
  relations, and final black-box acceptance.
- Still gated: unrelated repositories, unrelated Cloudflare resources,
  unrelated deployment/database data, and PR merge when its current upstream
  gate is not green. Record exact identities, commands, rollback units, and
  expected observations before the first remote mutation in each stage.

## Delivery Stages

1. **HLD and PoC** — freeze native schemas/APIs, Python upload/Simple behavior,
   MF snapshot contract, Host SDK state ports/consumers, reset migration, and
   cutover rollback; prove only named technical risks. **Completed for the
   three architecture-changing risks; remaining checks are implementation
   gates.**
2. **Registry** — replace target contracts/storage/API/CLI with native Python and
   MF surfaces; remove shared Runtime/API packages and rejected checks; verify
   local black-box publication and consumption.
3. **Core** — create one canonical Extension Host and one empty canonical table;
   remove bundle/binding/legacy paths; package and test six wheels; prepare
   native publication CD.
4. **Web** — create one canonical Extension Host over MF, remove binding/matcher/
   shared Runtime package, regenerate DB contract, and prepare native Remote CD.
5. **Rehearsal** — run the exact clean reset and end-to-end lifecycle against
   disposable local resources; prove rollback and unrelated-data preservation.
6. **Delivery handshake** — present exact diffs, commits, remote resources,
   credentials, commands, expected downtime, and rollback for authorization.
7. **Public-demo cutover** — after authorization, publish, reset, deploy, run the
   lifecycle acceptance, and retain machine-readable evidence.

## Current State

- Product/review Batches 01–04 are accepted.
- Disposable PoCs proved native wheel/Simple, MF manifest, and Worker multipart
  boundaries; see `work/16-native-distribution-pocs.md`.
- Registry implementation is locally complete. Its generated contracts, format,
  lint, type checks, 30 tests, package build, Worker dry build, fresh local
  D1/R2 migration, real `uv publish`/`uv pip install`, and native MF
  publication/read smoke all pass. Its root read-only catalog projects the same
  published Extensions as `/v1/extensions`; the Worker configuration freezes
  `registry.inkcre.dev` as both Custom Domain and canonical origin.
- Client Web implementation is locally complete and its frozen install, full
  repository contract, native Twitter `0.1.1` build/manifest closure, delivery
  workflow lint, and lifecycle/state tests pass. Its generated database files
  remain deliberately stale until an exact post-cutover Core image exists; the
  PostgREST adapter contains one narrow temporary type seam and no legacy runtime
  fallback.
- Core implementation and Review Batch 05 remediation are locally complete on
  its isolated native-cutover branch. No commit, push, release, public Registry,
  Cloudflare, or deployment-database mutation has occurred.
- Core's pinned PDM 2.27.0 repository contract passes with 217 tests and zero
  Pyrefly diagnostics. Disposable PostgreSQL also proves the RPC/ACL/trigger and
  concurrent-install boundaries. A separate rehearsal committed populated
  legacy `extensions`, `extension_installations`, and
  `extension_peer_bindings`, then ran the real hard-cut upgrade in a new
  transaction: the result was one empty canonical `extensions` relation and the
  enabled RPC, while the existing Client row and an unrelated sentinel relation
  remained byte-for-value unchanged. A deliberately unrealistic same-transaction
  setup first reproduced PostgreSQL's pending deferrable-trigger DROP refusal;
  separating pre-existing state from the migration matched deployment timing and
  passed.
- All six wheels build, install together into one ordinary disposable
  site-packages, load through standard entry points, expose modules from their
  installed Distribution paths, and complete the Host lifecycle with config
  and schema persistence. Production Core no longer carries Extension-only
  `datadot`; the Twitter wheel owns that dependency.
- A fresh isolated local Worker then accepted the real Core Twitter wheel and
  the real Web Twitter MF snapshot into the same `inkcre/twitter@0.1.1`
  Release. The exact descriptor exposed both native associations with their
  distinct Host SDKs; Simple JSON, wheel SHA-256, PEP 658 metadata, absolute MF
  `publicPath`, CORS, immutable caching, and exact `remoteEntry.js` bytes all
  matched their checked producer artifacts. Repeating both prepare requests,
  the wheel upload, and the MF upload with identical association provenance and
  bytes returned success, proving the intended same-run delivery retry lane.
- The deployment state port is being converged on one canonical `extensions`
  relation plus an atomic server-owned per-Peer `enabled[]` mutation; neither
  Host SDK may depend on SQL table shapes or perform a client-side
  read-modify-write.
- Existing production implementation and acceptance evidence remain the baseline
  against which deletions and retained lifecycle behavior are verified.

## Immediate Next Step

Execute the authorized delivery handshake and cutover in dependency order.
Because the
Web contract generator consumes an exact Core image whose source revision is
part of generated truth, final Web contract synchronization belongs after
Core merge/image delivery and before the final Web delivery. Likewise, create
fresh Registry D1/R2 resources and write their exact bindings before deploying
the Registry revision; never deploy the native schema against the deliberately
stale bindings. Preserve the Web typed adapter seam until `contract:sync`; do
not fabricate a local image identity to make the generated files appear
current. Stop at any failed gate rather than advancing the downstream merge.

## Authorized Execution Batch — 2026-08-11

### Registry production impact handshake

- **Address and object**: Cloudflare account
  `5c21142473f771b49ee6da743900e842`; Worker
  `inkcre-extension-registry`; Custom Domain `registry.inkcre.dev`; new D1 and
  R2 resources named `inkcre-extension-registry-production-v2`; D1 ID
  `af52114f-55b5-476f-b986-8ff8d8601d77`; GitHub PR
  `InKCre/ext-reg#5` at `c1e381a77a815256b0804106d6fafe6ab3a7d53e` before
  delivery-specific commits.
- **State diff**: the Worker currently runs the pre-cutover implementation with
  D1 `inkcre-extension-registry-production`
  (`7288f832-7def-4877-aef8-2e6f613458fe`) and same-named R2. It will run the
  native implementation against fresh `-v2` resources. The old resources will
  not be modified or deleted in this batch.
- **Operation**: create fresh D1/R2; freeze the returned D1 ID in
  `wrangler.jsonc`; apply `migrations/0001_registry.sql`; seed only namespace
  `inkcre` plus one hashed scoped publisher credential; store its plaintext as
  the selected-Repository organization Actions secret
  `INKCRE_EXTENSION_REGISTRY_TOKEN` for `core-py` and `client-web`; deploy the
  exact merged Registry main revision and perform anonymous read smoke.
- **Blast radius**: Registry catalog/control/native Distribution endpoints and
  first-party publisher workflows. No deployment database, Peer runtime, or
  unrelated Cloudflare resource changes occur in this stage.
- **Invariants**: `registry.inkcre.dev` remains the canonical public origin;
  anonymous read stays public; publisher writes remain namespace-authenticated;
  no old D1/R2 deletion; no preview-resource reuse; no downstream PR merge until
  Registry smoke is green.
- **Verification**: full Registry contract on the exact revision; D1 migration
  list and expected native table set; empty catalog before publication;
  `/livez`, `/`, `/v1/extensions`, `/simple/` HTML and JSON; Worker deployment
  identity and Custom Domain; authenticated prepare is deferred to the first
  Core wheel publication and must not expose the credential.
- **Rollback unit**: the pre-cutover Worker Version/deployment remains available
  and carries its old D1/R2 bindings. Rollback deploys that exact Version; fresh
  `-v2` data remains isolated for diagnosis. Resource deletion is outside this
  batch.
- **Known uncertainty**: the existing organization Cloudflare deploy token was
  proven for preview Worker/D1/R2 operations; production Custom Domain mutation
  may require an additional route/domain permission. The first exact production
  workflow run is the authority test and must fail closed before any Peer merge.

### Downstream ordered mutations

1. Mark `ext-reg#5` Ready, merge only on green checks, deploy its exact `main`
   SHA, and complete Registry smoke.
2. Mark and merge `core-py#50`; allow its protected-main workflows to hard-cut
   only the three Extension-state relations, publish the exact Core image, and
   publish six wheels to the now-green Registry. Preserve unrelated deployment
   relations/data.
3. Resolve the exact promoted Core image digest and run `client-web`'s owned
   `contract:sync`; remove the temporary generated-type seam, commit/push that
   bounded result to PR `client-web#63`, and require every check to pass.
4. Mark and merge `client-web#63`; publish the exact checked Twitter MF snapshot
   and deploy the exact checked Pages artifact.
5. Run the cross-repository black-box lifecycle. Any failed upstream observation
   halts the sequence and leaves downstream PRs unmerged.

### Registry provisioning evidence

- Created D1 `inkcre-extension-registry-production-v2` in APAC with ID
  `af52114f-55b5-476f-b986-8ff8d8601d77` and R2 bucket
  `inkcre-extension-registry-production-v2` in APAC/Standard. The pre-cutover
  D1/R2 remain present and unchanged.
- Applied `0001_registry.sql` remotely to the new D1: one migration, eleven SQL
  commands, success. Seeded only namespace `inkcre` and one active credential
  label `github-actions-first-party`.
- Generated the publisher token once in process. D1 stores only its SHA-256;
  GitHub stores the plaintext as the organization Actions secret
  `INKCRE_EXTENSION_REGISTRY_TOKEN`, selected only for `core-py` and
  `client-web`. No plaintext was written to disk, command output, or task
  evidence.
- Replaced the stale production bindings in `wrangler.jsonc` and changed the
  protected manual workflow from a non-mutating handoff into exact-main
  verify→migrate→deploy→anonymous-smoke delivery. Resource creation/deletion is
  deliberately absent from the workflow.
- Local contract after this change: 31 tests, formatting, lint, Pyright, package
  builds, and Worker dry build all pass; the dry build reports only the new D1,
  new R2, and `https://registry.inkcre.dev` bindings.
