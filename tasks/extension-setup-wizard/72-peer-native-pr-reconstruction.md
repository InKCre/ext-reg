# Peer-native PR Reconstruction

## Result of the Preview Diagnosis

Core PR #52 head `5804f73` is based on the old technical Client domain and does
not contain `app.business.peer`, `inkcre.peers` or
`scripts/configure_peer_runtime.py`. Current Core main already admitted the
hard Client-to-Peer cutover, exact capability advertisement, deployment config,
global Job/Cron runtime and a materially revised Source/Extension Host.

The failed preview therefore revealed a stale feature baseline. It did not
justify making current main's controller conditionally skip its own Peer
contract. Core PR #62 is not part of the solution.

## Chosen Integration Shape

Keep Core PR #52 and Client PR #68 as the review surfaces, but rebuild their
contents on admitted upstream truth:

```text
current core-py main (Peer authority)
  + Extension state/setup/Twitter 0.2.0
  + Peer/deployment Registry origin resolution
  -> exact Core feature image and database contract
    -> client-web PR #68 contract sync
      + Web Peer runtime/SDK
      + Peer selector/settings and capability invocation
      + Twitter setup contribution
```

Do not merge old main into PR #52 and mechanically resolve thousands of lines,
and do not cherry-pick the old 35-file setup commit over current main. Both
would resurrect deleted Client, Source scheduler and Host structures. Build a
clean integration branch from current `origin/main`, reapply the accepted
product behavior against current APIs, verify it, then update PR #52's existing
remote head with `--force-with-lease` against its observed old SHA. Preserve the
old remote/local heads as recovery refs until the rewritten PR passes.

The two local JWT commits on the old worktree are not replayed: current main PR
#61 already owns the unified signing authority. The uncommitted Client-based
Registry resolver is retained only as behavioral evidence and is reimplemented
through Peer/deployment authority.

## Core PR #52 — Exact Implementation Plan

### 1. Canonical Extension state on current schema

- Add `extensions.state JSONB NOT NULL DEFAULT '{}'` with a new append-only
  revision from current main's migration head; do not reuse the old branch's
  `c7d8e9f0a1b2` revision.
- Advance the current database contract/protocol projections and exact role/
  trigger checks. Preserve `peers`, `configs`, Jobs, Crons and every unrelated
  relation.
- Port the accepted `InstalledExtension`/`ExtensionStore` naming, typed
  config/state reads and Core-owned row-lock mutation callbacks.
- Keep config writes explicit and remove stale config persistence from base
  `on_close()`. Reject version change when state is non-empty at both Core and
  database authority boundaries.

### 2. Peer-native Host and callback lifecycle

- Keep `PeerManager.get_current_peer_ref()` as the only runtime identity for
  enable, disable and cold restore.
- Port the exact public-route claim into the current publication snapshot so
  only `GET /twitter/auth/callback` bypasses Peer JWT while Twitter is running;
  teardown withdraws the claim.
- Retain the current Extension management capability
  `core.extension.management.v1`; do not revive direct Client management.
- Add one Twitter-owned typed capability, `inkcre.twitter.setup.v1`, backed by a
  fixed authenticated Peer HTTP inbound. It carries discriminated setup
  commands/results for status, OAuth App save, begin/poll/disconnect, bookmark
  Source selection and Finish. It is advertised only while Twitter is running
  and is withdrawn before teardown. The public OAuth callback is not sent
  through this capability.

### 3. Registry and callback address authority

Add one deployment-wide Extension Registry config contract and an
owner-specific override in each Host Peer. The Core resolution path is:

```text
CorePeerConfig.extension_registry_url (non-empty override)
  > configs[extension.registry].extension_registry_url
  > settings.extension_registry_url
```

Validate every configured value as one HTTP(S) origin. Resolve it at the start
of each Registry-backed Host operation and pass one immutable snapshot through
the exact Release request and pip/Simple acquisition. A malformed explicit
override fails closed.

The Twitter redirect URI is derived from the executing Core Peer's validated
`CorePeerConfig.http_public_base_url`, which preview/production delivery already
converges. Do not restore `CLIENT_BASE_URL`, infer a request origin or add a
Web/Core `postMessage` channel.

### 4. Twitter setup on current Source, Cron and Job authorities

- Port the Authlib PKCE/account/transaction state machine onto the current
  Twitter/graph code; do not overwrite current bookmark graph production with
  the old branch implementation.
- Keep the Twitter setup wire concept `collect_at`, but project it to the
  current Cron domain rather than restoring removed `sources.collect_at`.
  Twitter state records only selected `bookmark_source_id` and the selected
  setup Cron reference; Source, Cron and Job rows remain their own authorities.
- Reuse ordinary Source creation, add explicit Core Cron create/update methods,
  and use the existing run-now operation for the initial Job. UI pending state
  handles normal double-submit; rare duplicate Sources/Jobs are accepted for
  this single-user product.
- Bind Cron and initial Job parameters to the current opaque
  `authorization_id`. Reconnect makes prior work ineligible; Finish rebinds the
  selected schedule and enqueues one bounded collection Job.
- Uninstall deletes only the Extension row. It does not inspect or delete
  Sources, Crons or Jobs; their domains retain unreachable-type behavior.
- Advance Core Host SDK and Twitter Python Distribution to the already accepted
  versions and re-run the six-wheel/site-packages lifecycle proof.

### 5. Core verification

Run focused pure and disposable-PostgreSQL tests for:

- state migration, role/trigger authority and non-empty-state version gate;
- Peer override/deployment/process Registry precedence and one-operation
  snapshot;
- exact public callback claim and Twitter setup capability advertisement/
  withdrawal;
- OAuth restart/replay/overlapping transactions and bounded error redaction;
- Source creation, Cron schedule projection, Finish enqueue and reconnect
  authorization races;
- current Twitter graph collection, empty results and wheel lifecycle.

Then run repository-pinned full checks, migration integrity, offline SQL,
schema/runtime contract generation and `git diff --check`. Build the exact final
Core image and run its preview database/readiness contract before updating the
remote PR head.

## Client PR #68 — Dependent Peer Migration Plan

After the exact Core feature image is green:

1. Sync generated database/runtime contracts from that image. The technical
   relation is `peers`; no `clients` compatibility type/table remains.
2. Replace the technical `Client` active record with `Peer`/`PeerRef` and a
   small Web Peer runtime that registers this browser's generated Peer ID,
   publishes an empty capability snapshot, renews its lease while active and
   stops renewing on shutdown so database-time expiry owns liveness. Its
   owner-specific config schema retains `extension_registry_url`, using the
   same Peer-override/deployment-default/library-fallback order as Core.
   Product/repository wording such as `client-web` and ordinary user-facing
   “Client” may remain where it does not describe the technical runtime node.
3. Implement the shared Peer HTTP v1 consumer on the library happy path:
   discover live exact capability advertisements, issue the normalized
   authenticated envelope and preserve the protocol's no-replay boundary.
4. Rework the selector/control coordinator:
   - current Web Peer -> local Web Host lifecycle;
   - selected Peer advertising `core.extension.management.v1` -> exact
     capability invocation;
   - selected Peer without that capability -> atomic desired-state RPC only.
5. Rework Settings to list/manage Peer rows. Core-owned
   `extension_registry_url` appears through the Core Peer config schema; the
   deployment default remains the deployment-config resource, not browser meta
   config.
6. Rework Twitter candidate discovery to use live
   `core.extension.management.v1` Peers and `inkcre.twitter.setup.v1`, not
   `Client.list()`, `rest_api_url` or probing arbitrary origins. The wizard
   keeps its current four-step/close UI and talks only through the typed Twitter
   capability.
7. Re-run generated-contract checks, Web Peer/protocol/selector/settings/setup
   tests, Twitter MF build/closure, full `pnpm check`, actionlint and
   `git diff --check`.

## Delivery and PR Sequence

1. Reconstruct and verify Core locally.
2. With separate commit/push authorization, force-with-lease update existing
   Core PR #52; wait for its repository, database and Peer preview checks.
3. Build the exact checked Core head and sync Client PR #68 to it.
4. Verify Client locally, then ordinary commit/push under separate authority;
   wait for its checks and Pages preview.
5. Run the bounded cross-preview gate: browser Peer registration, Extension
   list/selector, enable Twitter on the chosen Core Peer, setup contribution,
   callback URL and wizard entry. Real provider OAuth remains Sir-owned unless
   separately delegated.
6. Close PR #62 as superseded only with explicit remote-state authorization.
   Do not merge any PR in this batch.

## Readiness Decision

Investigation, topology review and implementation planning are complete. The
source batch is ready to begin only after Sir explicitly authorizes this
Peer-native reconstruction. Source edits do not imply permission to commit,
rewrite/push PR #52, push PR #68, close PR #62, deploy previews or merge.
