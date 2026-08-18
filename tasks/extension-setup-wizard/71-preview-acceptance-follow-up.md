# Preview Acceptance Follow-up

## Status

Local implementation and repository verification are complete. The changes are
not committed or pushed, and no preview or other remote state was mutated. The
two changes below form one adjacent preview-acceptance batch.

## Finding 1 — The setup popup cannot be exited early

The popup shell correctly belongs to `client-web`, while the complete Twitter
setup experience belongs to the Twitter Web Distribution. The shell disables
its own cancel/confirm controls and mounts the contribution's `close` event.
Twitter already emits that event, but renders its Close button only on the last
step. Consequently the user cannot exit while loading or from steps 1–3.

### Accepted correction

Twitter owns one always-available Close action outside the step-specific
panels. The existing final-step-only Close action is removed rather than
duplicated. Closing unmounts the Twitter contribution through its existing
`close` event, which already aborts polling and in-flight wizard work; durable
configuration, state and Sources are not rolled back.

Do not restore a Host-owned dialog button, change the Host contribution API,
or add a regression test for this presentation correction. Run the existing
Twitter wizard and repository checks.

## Finding 2 — Core ignores the current Client's Registry override

Core currently constructs the process-global `ExtensionHost` with two objects
whose Registry origin is copied from `settings.extension_registry_url` at
module import time:

- `RegistryReleaseClient`, used for the exact Release descriptor;
- `PipDistributionConsumer`, used for the Python Simple index and wheel.

Neither path reads `clients.config.extension_registry_url`. Editing that Client
configuration therefore cannot affect install, enable or cold restore, and the
reported `Registry could not resolve inkcre/twitter@0.2.0` is expected whenever
the process-level origin points at a Registry without that Release.

### Accepted precedence and scope

For the current Client-based branch, the effective Registry origin is:

1. the current Core Client's non-empty `config.extension_registry_url`;
2. the existing process setting/default.

The Client override is read from authoritative storage at the start of every
Registry-backed operation, so an operator's saved change applies without a
Core restart to the next install or enable. An invalid non-empty override fails
with a configuration error rather than silently falling back.

When Peer/deployment configuration is admitted later, only the resolver's
precedence expands:

`Client override > deployment Registry URL > process fallback`.

This batch does not backport the origin/main deployment/Peer configuration
model.

### Per-operation consistency

One operation snapshots one effective origin. Exact Release resolution and the
subsequent Simple-index/wheel acquisition must consume that same value; they
must not independently reread mutable Client configuration and accidentally
mix two Registries.

The implementation therefore makes the origin an explicit per-operation input
to the Release resolver and Distribution consumer. `ExtensionHost` owns the
dynamic Client-aware provider and takes the snapshot before resolution. The
existing process setting remains a fallback, not a separately active Registry
lane.

## Source Change Map

### Client PR #68

- `extensions/twitter/src/components/twitterSetupWizard/twitterSetupWizard.vue`:
  move the Extension-owned Close action outside step-specific content;
- `twitterSetupWizard.scss`: only the minimal alignment needed for that action;
- no Host dialog, contribution API, locale or test changes.

### Core PR #52

- `app/business/extension/main.py`: resolve the current Client-aware origin for
  each Registry-backed operation and retain one snapshot through resolution and
  acquisition;
- `app/business/extension/release.py`: validate/normalize an explicit Registry
  origin and accept it per exact Release request;
- `app/business/extension/distribution.py`: accept that same explicit origin for
  Simple-index/wheel acquisition instead of retaining a constructor-time
  origin;
- existing Core Host tests/fakes are updated for the interface; focused tests
  lock Client override, fallback, invalid override and same-operation origin
  consistency.

No database schema, Registry service, deployment configuration, generated
contract, delivery workflow or public Release changes are part of this batch.

## Verification Plan

- run the existing Twitter wizard suite without adding a new presentation
  regression test;
- run focused Core Host/Release/Distribution tests, including dynamic Client
  override and one-operation origin consistency;
- run `pnpm check` in Client and the pinned full Core repository check;
- run `git diff --check` in both repositories;
- do not commit, push or mutate previews without separate authorization.

## Implementation Result

- Twitter now renders one Extension-owned Close action after the conditional
  wizard content, so it remains available while loading and on every step. The
  prior final-step-only action was removed. No Host code, contribution API,
  locale or test changed.
- Core resolves the current Client's Registry override dynamically for each
  Registry-backed operation. Empty/missing override falls back to the process
  setting; a malformed non-empty override fails closed.
- Release resolution and Python Distribution acquisition now require the
  Registry origin as an explicit per-operation argument. Neither concrete
  consumer retains a second constructor-time Registry authority.
- One Host operation invokes its provider once and passes that exact normalized
  origin to both consumers. Existing tests/fakes were adapted, and focused Core
  tests cover override/fallback/invalid values and the one-snapshot invariant.
- Client `pnpm check` passed: 27 test files / 110 tests plus every workspace
  type-check, build and package contract.
- Core focused checks passed: 49 tests and 0 type diagnostics. The full contract
  passed under the repository-required isolated PDM 2.27.0: 254 tests, format,
  lint, type, migration and lock checks.
- `git diff --check` passed in both source repositories. The first attempt to
  run Core's full check with the host PDM 2.28.0 stopped at the intentional
  version guard before any project check; rerunning with PDM 2.27.0 passed.

## Preview Controller Diagnosis — Superseded

Core PR #52's failing Preview application run `31774435213` successfully built
the candidate image, initialized the preview database, published both Heroku
apps and configured PostgREST. It failed only when the current main-owned
controller invoked `/app/scripts/configure_peer_runtime.py` inside the old
Client-based candidate image.

The prior recommendation to admit Core PR #62 is rejected. A fallback that
skips Peer convergence would make current main's delivery controller support a
candidate that cannot satisfy the repository's admitted Peer runtime contract.
The correct repair is to reconstruct PR #52 from current main and port the
feature onto Peer authority. The resulting image contains
`configure_peer_runtime.py`, registers the exact Peer, publishes its capability
snapshot and passes the existing controller without a legacy branch. See
[Peer-native PR reconstruction](72-peer-native-pr-reconstruction.md).
