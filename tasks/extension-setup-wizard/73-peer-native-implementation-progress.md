# Peer-native Implementation Progress

## Batch Status

Sir authorized source implementation after approving the reconstruction plan in
`72-peer-native-pr-reconstruction.md`. The implementation is active in two new,
uncommitted worktrees; the obsolete Client-based PR worktrees remain untouched
as recovery/reference surfaces:

- Core: `feat/extension-setup-wizard-core-peer`, based on current Core main;
- Client: `feat/extension-setup-wizard-web-peer`, based on the admitted
  synchronized Peer branch.

No commit, push, PR rewrite, Release publication, preview deployment or merge is
authorized by this source batch.

## Core Result So Far

- Added canonical deployment-wide `extensions.state` plus database-authority
  config/state mutation and non-empty-state version gates. Core runtime alone
  receives column-level state-update authority; generic management responses
  exclude Extension-produced state.
- Ported Twitter 0.2.0 OAuth App/account/PKCE transaction, standalone callback,
  Bookmark Source, Cron and initial Job setup onto current Peer/Source/Cron/Job
  authorities.
- Published `inkcre.twitter.setup.v1` only while Twitter is running and retained
  `core.extension.management.v1` for exact selected-Peer control.
- Added operation-time Registry resolution:
  executing Core Peer override, deployment config, then process/product fallback.
- Browser registration uses an ordinary `peers` upsert from the Web runtime.
  Its payload contains only runtime-owned `id`、`name`、`config_schema` and
  `capabilities`, so owner-authored `config` and `labels` remain untouched.
- Advanced the Core Host SDK to 0.1.1 and the Twitter wheel to 0.2.0.
- Redacted OAuth query material from request diagnostics, reconciled a direct
  deployment config change before Twitter setup becomes reachable, and disabled
  the setup-owned Cron whenever the OAuth App/account is replaced or
  disconnected. The Source and Cron records remain reusable and uninstall still
  does not inspect Source-domain records.

Latest pinned full evidence:

```text
pdm run check
  foundation/lock/migrations/format/lint/type checks: passed
  pyrefly: 0 diagnostics
  pytest: 488 passed, 41 skipped
```

## Client Result So Far

- Meta config now generates and persists one browser-origin Peer UUID and
  migrates a legacy Client UUID if present; `INKCRE_CLIENT_ID` is no longer a
  required environment/config input.
- Saving Settings validates JWT/database connectivity, registers the Web Peer,
  starts its lease runtime, saves owner config and replaces the local bootstrap
  only after the whole candidate connection succeeds. Reconnect/reset stops the
  prior runtime, and the Settings recovery route does not cold-start Extensions
  before the Peer override is available.
- The Web Peer runtime performs the runtime-field-only upsert, renews a
  database-time lease and stops renewal on shutdown.
- Registry origin resolution is current Peer override, deployment config, then
  `https://registry.inkcre.dev`, with one origin snapshot per exact Release read.
- The Extensions page restores the product-facing Client selector over Peer
  rows. Current browser uses the local Web Host, an advertised remote Host uses
  exact capability delegation, and every other Client uses the atomic durable
  desired-state RPC.
- Web Extension API now has one optional setup component contribution. The Host
  exposes it only while the current Web runtime is active; setup availability is
  independent of the selected Client.
- Twitter Web 0.2.0 owns the four-step wizard and its always-available Close
  action. It discovers live Core Peers and sends every management/setup command
  through exact Peer capabilities; no Client REST origin probing or postMessage
  dependency remains.
- Generic Extension list/get/mutation responses now request an explicit
  management projection and never fetch `extensions.state` into the browser.
  Registry/provider URLs reject non-HTTP(S) schemes and embedded authority
  credentials.

Latest full evidence:

```text
pnpm check
  format/lint/database/runtime/workspace contracts: passed
  type checks: all 6 workspaces passed
  Vitest: 36 files, 136 tests passed
  builds and browser package contract: passed
actionlint 1.7.12: passed
git diff --check: passed
```

The added coverage includes Web Peer registration/lease, bootstrap transaction,
Registry authority, exact selected-Client control modes, setup contribution
lifecycle, Twitter capability transport, selector projection and the explicit
Core-enable wizard transition. It deliberately does not add the rejected
Twitter Close-button regression test.

## Remaining Cross-Repository Gate

1. The Client generated database files still describe the prior exact Core
   image. Local Docker is unavailable and the configured SSH Docker provider is
   unavailable. The Core feature migration head is now `c6d7e8f9a0b1`; generated
   files remain deliberately untouched until an exact image exists.
2. After separate commit/push authority produces the exact Core feature image,
   sync the Client database/runtime evidence from that image and rerun
   `pnpm check` before Client merge. There is no temporary `register_peer` type seam.

All temporary PostgreSQL clusters and failed type-generation output created by
the rehearsal were stopped and moved to Trash. No unrelated local database was
touched.

Black-box provider acceptance remains Sir-owned and deferred. The source batch
ends at PR-ready-for-review evidence, not merge or publication.
