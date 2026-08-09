# MVP Acceptance

## Product Gate

- The product model in [`15-product-design.md`](15-product-design.md) is complete and internally consistent.
- Public Registry state, deployment installed state, per-peer enabled state, and runtime running state remain separate.
- Explicit non-goals remove dependency graphs, self-service namespace management, advanced security/moderation, upgrade orchestration, and uncontrolled drift handling from MVP.

## HLD And Pre-implementation Gate

- HLD selects mature service, metadata database, artifact storage, publisher authentication, and peer-adapter boundaries that preserve the product model.
- Any PoC names one design-changing risk and uses the smallest experiment needed to resolve it.
- A cross-repository implementation plan maps authoritative files, migrations, workflows, production configuration, rollback, and verification.
- A written mental rehearsal covers publish races, shared-version installation, per-peer lifecycle, uninstall persistence, secrets, and deployment ordering before implementation begins.

## Registry Gate

- Public production exposes anonymous metadata/artifact reads and scoped authenticated publication.
- Two independent uploads append different immutable target keys to one exact Extension Version.
- Same target/digest retry succeeds idempotently; same target/different digest conflicts.
- Published metadata resolves exact content digests; install/enable rejects unavailable or mismatched bytes without mutating deployment state.
- One small black-box E2E suite covers the publish/read/conflict path; broad edge-case and security suites are not required.

## Peer Contract Gate

- Both peers consume the Runtime/API and Registry target contract owned by this project rather than their previous local-only/hard-coded Registry behavior.
- All peers sharing the database observe one installed `namespace/name@version` while binding peer-specific target digests.
- Installation starts disabled; enable succeeds only after compatible target admission; disable removes runtime side effects; uninstall persists across restart and requires all peers disabled.
- `core-py` does not execute unadmitted arbitrary live-downloaded Python code; `client-web` loads the exact bound Module Federation artifact and coherent assets.

## Publisher CD Gate

- A `client-web` feature branch based on current `origin/main` builds one existing first-party Extension target and publishes it through CD to the production Registry.
- A `core-py` feature branch based on current `origin/main` builds one existing first-party Extension target and publishes it through CD to the same product version.
- Each workflow records source revision, target key, and exact digest. First-party uses reserved `inkcre` policy rather than a special publish protocol.

## Production MVP Gate

- The `InKCre/ext-reg` repository and public Registry production deployment exist.
- Registry, `client-web`, and `core-py` production revisions are traceable to committed source and successful delivery runs.
- Production Registry shows both peer-published target artifacts under one Extension Version.
- Against the real shared production database, the selected Extension is installed, enabled and observed running on `client-web`, enabled and observed running on `core-py`, disabled on both, then uninstalled.
- The final database and peer/runtime observations prove `absent → installed/disabled → peer-bound/running → disabled → absent`; HTTP success alone is insufficient.
