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
- Still gated: PR merge, releases/publication, GitHub secret writes, Cloudflare
  resource mutation, deployment database mutation, and live service cutover.
  Before that batch, record exact repositories/revisions, resources, commands,
  rollback unit, and expected observations.

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

Execute the delivery handshake only after separate authorization. Because the
Web contract generator consumes an exact Core image whose source revision is
part of generated truth, final Web contract synchronization belongs after
authorized Core commit/image delivery and before the final Web commit/delivery.
Likewise, create fresh Registry D1/R2 resources and write their exact bindings
before committing/deploying the Registry revision; never deploy the native
schema against the deliberately stale bindings. Preserve the Web typed adapter
seam until `contract:sync`; do not fabricate a local image identity to make the
generated files appear current. The exact clean demo reset targets must be
reviewed before any remote mutation.
