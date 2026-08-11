# Review Batch 05 — Native Implementation Integrity

## Scope

Audit whether the locally implemented native cutover actually preserves the
accepted security, lifecycle, deployment-state, and checked-artifact boundaries.
Passing repository tests are evidence, not a substitute for this review.

## Status

Complete. Every confirmed local finding is remediated and independently
reverified. No commit, publication, deployment, or remote mutation is
authorized by this batch.

## Registry Findings And Disposition

The first independent Registry review found one remote-delivery blocker and
five native-admission defects:

- the rewritten initial D1 migration could have been aimed at the old bound
  resources;
- PEP 440-normalized aliases could pass a stricter Release-version mapping;
- state-dependent negative responses were cacheable;
- generated schemas omitted canonical Name and strict SemVer patterns;
- wheel paths admitted non-canonical aliases; and
- native MF JSON accepted non-finite values that browsers reject.

All are locally remediated and covered by the 29-test repository contract plus
a fresh real-Worker smoke. The manual production workflow is now deliberately
non-mutating: it only rechecks one exact main SHA and records that new D1/R2
bindings remain a later delivery-handshake prerequisite.

## Core Findings And Required State Diff

The second independent review found four execution blockers:

1. Telegram's wheel loads an endpoint annotation whose type exists only under
   `TYPE_CHECKING`.
2. `authenticated` can directly update `extensions.enabled`, bypassing the
   atomic Peer RPC.
3. pip can mutate Core before proving that a differently named wheel owns only
   its declared namespace and does not overwrite Core or another Distribution.
4. withdrawing source-type registration does not stop scheduler jobs that have
   already captured bound Extension methods or clear cached Source instances.

The same batch must also close adjacent high-impact gaps:

- acquire/release the existing process-local runtime identity claim;
- download and freeze a dependency closure before mutation, and mark the
  interpreter restart-required after any failed mutation;
- make rapid consecutive main pushes neither lose an Extension publication nor
  publish a superseded Extension subtree;
- create Twitter runtime data directories without restoring source bytes to the
  image, persist base config cleanup even when Twitter cleanup fails, and use
  the registered bookmark Source type;
- persist and schedule newly enabled Source types, serialize concurrent first
  install by Extension Name, and report semantic conflicts.

The accepted implementation direction is:

- `enabled` may change only through a fixed-search-path `SECURITY DEFINER` RPC;
  database triggers require empty initial enablement and reject version change
  or deletion while any Peer remains enabled;
- authenticated table writes retain only the columns needed for install,
  version, nickname, and config operations;
- Core accepts only the declared `extensions.<entrypoint>` subtree and its own
  dist-info, rejects `.pth`/`.data`/foreign paths and file collisions before
  pip, and uses one downloaded closure for offline preflight and install;
- native publication activation owns Source catalog synchronization, job
  creation, job removal, and cached-instance removal as one reversible resource;
- checked SHA publication remains valid when newer main commits leave that
  Extension subtree unchanged, and rechecks the subtree immediately before
  Registry mutation.

## Verification Gate

- Real Telegram entry-point/lifecycle start succeeds.
- Disposable PostgreSQL proves direct `enabled` update denial, RPC success,
  invalid-Peer rejection, trigger guards, concurrent Peer updates, and
  serialized first install.
- Malicious wheel fixtures for Core paths, sibling Extension paths, `.pth`,
  `.data`, non-canonical paths, and installed-file collisions fail before the
  command runner reaches mutating pip.
- Source scheduler/caches are absent after disable and restored on re-enable;
  live enable makes new Source rows constructible.
- Failed pip mutation poisons further acquisition until restart; successful new
  installation and intentional same-project replacement follow their distinct
  restart semantics.
- Consecutive-push workflow fixtures cover Extension-unchanged and
  Extension-changed descendants and a final pre-mutation main comparison.
- Pinned Core full contract, six wheel start probes, Web state adapter tests,
  and cross-repository native journey remain green.

## Final Evidence

- Core's pinned PDM 2.27.0 contract passes migration history and offline SQL,
  Ruff/format, Pyrefly with zero diagnostics, and 217 tests.
- Disposable PostgreSQL proves the RPC, direct-column denial, invalid-Peer
  behavior, insert/version/delete guards, concurrent distinct-Peer updates,
  and serialized first install.
- Six built wheels install into one normal disposable site-packages, load only
  through standard entry points, originate from the installed Distributions,
  and complete `on_start -> on_close -> unpublish -> release_runtime`.
- Source lifecycle tests cover no-argument cron callbacks, atomic collect-job
  claim, bootstrap re-scheduling, runtime-created rows/instances, disable
  cleanup without durable-row deletion, and re-enable.
- Registry's 29-test contract, generated schemas, package build, Worker dry
  build, and fresh local Worker smoke pass. Web's 76-test full workspace
  contract and native Twitter MF build pass.
- Core production dependencies no longer retain the Twitter-only `datadot`
  package; it remains only in the wheel and the development test group.
