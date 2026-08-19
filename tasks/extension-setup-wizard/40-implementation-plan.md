# Implementation Plan

Sir authorized source implementation on 2026-08-13. Batches 1–5 are complete in
the two task worktrees; Batch 6 is complete through local review evidence and
cleanup. Commit, push, PR creation, publication, deployment, merge and real-X
black-box acceptance remain outside that authorization.

The executed evidence and implementation refinements are recorded in
[Implementation result](60-implementation-result.md). This file remains the
pre-implementation plan rather than being rewritten into a retrospective.

## Impact Handshake

- **Invariant changed**: one canonical installed Extension gains
  deployment-wide typed state; a running Extension may contribute one exact
  public route; an enabled Web Extension may contribute setup UI.
- **Authorities preserved**: Registry owns Releases/Distributions;
  Core/PostgreSQL owns installed config/state and concurrency; Source owns
  Source rows/jobs; each Host owns runtime lifecycle; Twitter owns setup/OAuth.
- **Consumer impact**: Core database contract advances to v3; Core and Web Host
  SDKs become `0.1.1`; Twitter becomes one cross-format `0.2.0` Release.
- **Failure posture**: callback and token refresh keep their required conditional
  semantics. Ordinary Source/Cron/Job commands optimize the single-user happy
  path; UI pending state handles normal double-submit and rare duplicate work is
  accepted rather than buying a new idempotency subsystem.
- **Delivery boundary**: two new PRs ready for review; no merge, publication,
  deployment or black-box acceptance.

## Batch 1 — Core Database and Host SDK

In a fresh `core-py` branch from current `origin/main`:

1. Add `extensions.state`, the insert/update authority rules and database
   contract v3 in:
   - `app/schemas/extension/main.py`;
   - a new append-only `migrations/versions/*.py`;
   - `migrations/metadata.py`, `migrations/revision-integrity.json`;
   - `app/database_contract/constants.py`, `roles.py`, readiness/protocol files;
   - `deploy/profiles/production.json` and generated schema/OpenAPI artifacts.
2. Rename the misleading installed-row state types and add Core-owned fresh
   config/state reads plus row-lock mutations in
   `app/business/extension/state.py` and exports/callers. In the existing locked
   install transaction, reject a different version when `state != {}`; do not
   install/import the incoming Distribution as a migration probe. Extend the
   database update trigger with the same rule so direct PostgREST cannot bypass
   it.
3. Add the generic state model/type parameters and runtime callbacks in
   `app/business/extension/main.py` and `runtime.py`; preserve
   `ExtensionBase.config` as a compatibility snapshot while adding
   `get_config()` for authoritative reads. Persist explicit config changes at
   command time and remove the base `on_close()` stale-snapshot write.
4. Add the exact public-route registry/claim (one focused new module), connect it
   to `ExtensionPublication`, and consume it in `JWTMiddleware`.
5. Remove raw query values from generic request logs. Twitter handles and maps
   callback/provider failures before they reach generic logging.
6. Advance root `pyproject.toml`, `app/version.py` and `pdm.lock` to Core
   `0.1.1`, adding the frozen Authlib/HTTPX baseline.
7. Update nearest durable Core extension/routing/deployment guidance only where
   the new public API or state contract makes existing guidance false.

Verification for this batch:

```text
PDM 2.27.0 frozen lock check
migration history and offline SQL checks
focused state/public-route/middleware tests
config command-time persistence and stale-Peer-disable regression test
empty-state version-change acceptance and non-empty-state rejection test
disposable PostgreSQL role/trigger/concurrency tests
database schema/runtime-contract generation
full pdm run check
git diff --check
```

## Batch 2 — Twitter Python Distribution

On the same Core branch:

1. Advance `extensions/twitter/pyproject.toml` to `0.2.0`, require Core
   `>=0.1.1 <0.2.0`, and declare Authlib/HTTPX.
2. Define validated config/state/setup DTOs in the Twitter package.
3. Replace the hand-written in-memory OAuth endpoints/client with the Authlib
   service and durable transaction/account protocol. Claim callback exchange
   once with `pending -> exchanging`; do not add a lease/reclaim path for a
   potentially consumed authorization code. A new Begin supersedes older
   non-terminal flows so late callbacks cannot replace the newer user choice.
4. Declare the exact public callback and implement standalone bounded responses.
5. Add setup projection, OAuth App, begin/poll/disconnect, bookmark Source and
   Finish endpoints.
6. Reuse `SourceManager.create()`, add explicit `CronManager.create/update()`
   operations, and use the existing `CronManager.run_now()` for Finish. Do not
   add setup idempotency keys, advisory locks or Job deduplication.
7. Fix empty-bookmark collection and restore each bounded official API operation
   from fresh durable config/state in a newly closed Authlib client; do not retain
   an official cross-operation singleton. Keep Twikit outside the setup UI and
   retain its local session only while its fresh config binding matches.
8. Give every successful account authorization an opaque `authorization_id`;
   bind Finish's Cron/initial Job config and readiness to that ID, and fail the job
   before provider work if reconnect raced with Finish. Then update Twitter/Core
   tests and wheel metadata/entry-point probes.

Verification for this batch:

```text
injected Authlib transport/time/random focused tests
restart/replay/overlapping-flow/conditional refresh, cross-Peer freshness and redaction tests
per-operation official client close and Twikit config-cache replacement tests
real PostgreSQL Source/Cron operations and current-account job tests
Twitter Source empty-result/first-job tests
build and verify all six first-party wheels
load/start/close Twitter wheel from site-packages
full pdm run check
```

## Batch 3 — Exact Core Contract for Client

1. Start a task-owned Core runtime through the configured SSH Docker provider
   from the exact Core feature branch.
2. Record the image tag, source revision, migration head and contract revision.
3. In a fresh `client-web` branch, configure the same SSH provider and run
   contract sync/check against that exact image.
4. Confirm generated `extensions` includes `state`, revision is v3, and no
   installation/binding relations return.
5. Stop the task-owned Core runtime after Client verification.

The official stop command removes the instance-owned Compose/volume/state/tunnel.
Do not delete the source-revision image tag or run a broad Docker prune: that
cache is not instance-owned and may serve another task.

This batch is a hard gate before Web source integration, not a later cleanup.

## Batch 4 — Web Host and Popup Shell

In the Client branch:

1. Advance `packages/core/package.json` to `0.1.1` and update the lock/workspace
   contracts.
2. Add `ExtensionSetupContribution`, store the loaded module in the running
   record, and expose setup only for a running Extension.
3. Extend Host tests for contribution lifecycle and absence while disabled.
4. Add optional `AbortSignal` propagation to the existing authenticated
   `Client.request` path. Its one-time 401 retry preserves body, signal and all
   non-auth headers while replacing Authorization; do not add a Twitter
   fetch/auth wrapper. Accept bounded string FastAPI `detail` errors without
   stringifying validation objects.
5. Add the Extension-card Setup action, disabled explanation and `InkDialog`
   shell; unmount the dynamic component and await one Vue tick before
   disable/unload, and leave the existing expert config editor intact.
6. Keep Host/popup free of Twitter/Core command semantics.

Verification:

```text
@inkcre/core type-check and Host tests
extension-card component tests in happy-dom
contract:check against the exact Core image
```

## Batch 5 — Twitter Web Distribution

1. Advance `extensions/twitter/package.json` to Extension `0.2.0`, require
   `@inkcre/core >=0.1.1 <0.2.0`, and update the lock.
2. Add Twitter-owned setup DTOs/API client and `TwitterSetupWizard.vue` plus
   focused step components/styles.
3. Implement reachable-Core discovery, explicit Core enable, credential setup,
   deliberate X link, bounded polling cleanup, Source selection/creation and
   Finish.
4. Export the setup component beside the existing lifecycle from the MF entry.
5. Update native manifest/distribution tests for the new versions and bundle.
6. Use existing UI components and ordinary Vue state; add no generic wizard,
   form framework, OAuth library or cross-Remote i18n protocol.

Verification:

```text
Twitter setup API/composable unit tests
Vue wizard resume/error/poll-cleanup tests
card -> dialog -> contributed component integration test
Twitter type-check/build and native mf-manifest closure check
full pnpm check
actionlint for unchanged delivery workflows
git diff --check
```

## Batch 6 — Review and PR Handoff

1. Review both diffs for authority leakage, secret/log exposure, state/config
   confusion, callback lifecycle and generated-contract provenance.
2. Repeat the read-only Registry lookup for `inkcre/twitter@0.2.0`; stop for
   version review if it is no longer unused.
3. Rebase/check against current upstream before committing.
4. After separate commit/push authorization, create two new branches, commit only
   task changes, push, and open two new PRs with the Core dependency recorded in
   the Client PR.
5. Wait for repository checks and fix only failures attributable to these PRs.
6. Keep Core independently green. Open Client as Draft/reviewable and record that
   its stable-Core workspace/E2E checks are an expected dependency gate, not a
   failure to bypass. Its exact unmerged Core image is valid review evidence;
   after Core lands, contract generation and checks must be refreshed against
   the admitted revision before Client can become merge-ready.
7. Stop at both PRs ready for Sir's review.

This handoff follows organization governance: each branch starts from its
repository's latest `main`; PR descriptions record intent, evidence, risk,
rollback, migration/delivery effects and the cross-repository dependency;
required checks are refreshed against the latest base; no direct `main` push,
production credential, canonical publication or merge is used. The two PRs are
cross-repository dependencies rather than one Git ancestry stack; merge order is
still Core first, then Client after refreshing its exact upstream evidence.
No Client workflow input or alternate image lane is added merely to make a
dependent Draft appear green before stable Core carries contract v3.

Explicitly excluded from every batch: merge, Registry publication, production
deployment, real-X black-box acceptance and cleanup of user-owned unrelated
worktrees.

## Concrete File and Test Map

The exact implementation may split a deep module when that improves
readability, but it must remain within these owned surfaces.

### Core branch `feat/extension-setup-wizard-core`

| Concern | Primary files | Focused evidence |
| --- | --- | --- |
| State schema/authority | `app/schemas/extension/main.py`, `app/business/extension/state.py`, `app/database_contract/*`, new Alembic revision | `tests/migrations/test_extension_registry_schema.py`, peer-role/RPC tests, new `tests/test_extension_state.py` |
| Host state API | `app/business/extension/main.py`, `runtime.py`, package exports/routes | existing `tests/test_extension_registry_runtime.py` plus typed-state and cross-Peer config freshness cases |
| Public callback | new `app/business/extension/public_http.py`, `runtime.py`, `app/middleware.py` | new `tests/test_extension_public_http.py`, `tests/test_jwt_contract.py`, logging tests |
| Twitter setup | `extensions/twitter/{__init__,api,schema,bookmark}.py` plus a focused setup/OAuth module | `tests/extensions/test_twitter.py` and new setup-focused tests |
| Source/Cron/Finish | `app/business/{source/main,cron}.py`, Twitter setup flow | Source/Cron operation and Twitter setup tests |
| Versions/dependencies | root and Twitter `pyproject.toml`, `pdm.lock`, `app/version.py` | `tests/test_extension_distribution.py`, six-wheel probe |
| Generated/durable truth | migration integrity, deployment profile, schema/OpenAPI and nearest guidance | migration/schema/deployment-profile checks |

### Client branch `feat/extension-setup-wizard-web`

| Concern | Primary files | Focused evidence |
| --- | --- | --- |
| Generated contract | `packages/core/src/database/database.generated.ts`, `runtime-contract.generated.json` | exact-image `contract:sync` then `contract:check` |
| Web Host API | `packages/core/src/extension/{model,host,index,postgrest-state}.ts`, `packages/core/src/client/client.ts`, package manifest/lock | Host tests, Client abort/401-retry/error tests and PostgREST omission of raw `state` writes |
| Card/popup | Extension card Vue/TS/SCSS/docs and Extensions view | new Extension-card component spec |
| Twitter wizard | `extensions/twitter/src/index.ts` and new `src/setup/*` | setup API/state/component specs |
| MF version/delivery | Twitter/package/core manifests, lock and existing MF verifier fixtures | native MF build/closure tests and actionlint |

## Exact Final Command Set

Core, using repository-pinned PDM behavior:

```text
pdm lock --check
pdm run check:migrations
pdm run test <focused test paths>
pdm run check
pdm run python scripts/dev_database.py ensure <task-instance>
git diff --check
```

Client, after resolving the exact remote-daemon Core image tag:

```text
pnpm install --frozen-lockfile
pnpm contract:sync -- --image <exact-core-development-image>
pnpm contract:check -- --image <same-image>
pnpm --filter @inkcre/core type-check
pnpm --filter @inkcre/client-web test
pnpm --filter @inkcre/ext-twitter type-check
pnpm --filter @inkcre/ext-twitter build
pnpm check
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 .github/workflows/*.yml
git diff --check
```

Stop the task-owned Core runtime with
`scripts/dev_database.py stop <task-instance>` after contract evidence. Any
command spelling that differs in the checked-out upstream must be reconciled
against that repository's own scripts before mutation; no ad-hoc replacement
check is acceptable.
