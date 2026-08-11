# Roadmap And Review Work Structure

## Operating Mode

The original generic-target MVP reached functional production acceptance. That
fact remains historical evidence, but the current task is a reviewed
architecture replacement rather than an incremental feature phase.

Work now advances through adjacent review/remediation batches:

```text
reported issue -> evidence -> diagnosis -> coherent replacement design
-> Sir review -> HLD/PoC -> local remediation -> verification
-> exact delivery authorization -> public-demo cutover
```

`review/` owns issue diagnosis and accepted dispositions. `work/` owns bounded
design/PoC/execution evidence. The numbered canonical files own current product,
decision, architecture, roadmap, and acceptance truth. An accepted review is
not marked remediated until code/schema/tests/automation and the local journey
have changed.

## Native Cutover Phases

### Phase N0 — Review Alignment

- **Status**: Complete.
- Vocabulary, direct shared deployment state, platform-specific Host SDKs,
  native Distribution surfaces, legacy diagnosis, and implementation-depth
  findings are accepted in Review Batches 00–04.

### Phase N1 — Native HLD And Architecture-changing PoCs

- **Status**: Complete.
- [`30-architecture.md`](30-architecture.md) is the native destination HLD.
- [`work/16-native-distribution-pocs.md`](work/16-native-distribution-pocs.md)
  proves six PEP 420 wheels/Simple selection, the native MF manifest/publicPath
  behavior, and the bounded Python Worker multipart lane.

### Phase N2 — Registry Remediation

- **Status**: Locally complete; independent diff review and remediation complete.
- Replace generic target/blob contracts with Extension/Release plus Python
  Simple/Upload and native MF surfaces.
- Recreate the D1 model without targets, host all native bytes in R2, remove the
  shared Web Runtime/API package, and replace target-oriented tests/workflows.
- Exit gate: local prepare/upload/publish/read/yank/idempotency/invalid-archive/
  CORS/cache black-box tests pass with no target vocabulary in production code.

### Phase N3 — Core Host And Six Wheels

- **Status**: Locally complete in the isolated `core-py` worktree.
- Add one canonical Extension relation via append-only hard-cut migration,
  remove binding/install tables and built-in seeding, implement one Python Host
  SDK over native acquisition/entry points, and package all six Extensions.
- Exit gate: local Simple install, contribution registration, lifecycle,
  config, cold restore, failure retention, migration/readiness/PostgREST, image,
  and full Core checks pass without checked-in production Extension bytes.
- The local exit gate is satisfied by the real six-wheel same-interpreter
  lifecycle probe, disposable PostgreSQL authority/concurrency tests, 217-test
  pinned repository contract, and Review Batch 05 wheel/Source/CD remediation.

### Phase N4 — Web Host And Native Remote

- **Status**: Locally complete except exact generated database contract synchronization.
- Implement one Web Host SDK over a semantic state port and native MF Host,
  remove binding/matcher/shared Runtime paths, emit the Twitter native manifest,
  and simplify UI and delivery.
- Exit gate: range precheck, cross-origin manifest load, lifecycle/state
  compensation, UI, generated database contract, checked artifact delivery,
  browser tests, and full Web checks pass.
- All source-owned Web gates pass. The generated contract gate remains blocked on
  an exact post-cutover Core image; a narrow type-only adapter seam makes this
  residual explicit and must be deleted immediately after `contract:sync`.

### Phase N5 — Local Cutover Rehearsal

- **Status**: Complete except the exact-image-dependent Web contract step.
- Exercise fresh Registry D1/R2 equivalents, the exact three-relation
  PostgreSQL reset, six wheel plus Twitter publication, Core/Web install-enable-
  disable-restart-uninstall, outage/yank/conflict behavior, and rollback.
- Prove unrelated deployment data is unchanged and no generic target/binding
  residue remains.

### Phase N6 — Delivery Handshake

- **Status**: Pending.
- Present exact repository branches/diffs/checks, commits to create, release
  versions, Cloudflare resources/bindings, GitHub secrets, maintenance effects,
  commands, expected observations, and rollback unit.
- Git commits, pushes, PRs, releases/publication, secret writes, Cloudflare
  mutation, deployment DB mutation, and live cutover remain stopped until Sir
  authorizes these exact objects.

### Phase N7 — Public-demo Cutover And Acceptance

- **Status**: Pending authorization.
- Publish native Distributions, cut over clean Registry resources, apply the
  bounded deployment hard cut, deploy both Host SDKs, run read-only and
  lifecycle acceptance, then delete old demo resources only after the rollback
  window closes.

## Current Work Files

- [`work/15-native-cutover.md`](work/15-native-cutover.md) is the execution
  control surface and authorization boundary.
- [`work/16-native-distribution-pocs.md`](work/16-native-distribution-pocs.md)
  owns the native PoC evidence and decisions induced by it.
- Earlier `work/09`–`work/14` files remain historical evidence for the rejected
  architecture; they are not current implementation instructions.
