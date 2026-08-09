# Decisions

## Status Vocabulary

- **Accepted**: approved direction for the current task; changing it requires an explicit decision update.
- **Provisional**: preferred direction supported by current evidence but awaiting a named proof point.
- **Open**: no responsible choice has been made.

## D001 — Registry Authority

- **Status**: Accepted.
- `ext-reg` owns the public hosted Registry service, publisher and namespace policy, Extension Version and target-artifact association, package/version admission, publish/read protocols, compatibility declaration validation and indexing, developer tooling, conformance fixtures, and release metadata.
- The Registry is authoritative for admitted publisher/namespace/Extension/version/target relationships and publication state. An artifact store owns bytes beneath that service boundary but does not independently define package meaning.
- Deployments own installation/configuration and peer/client enablement; runtime processes own active side effects.

## D002 — MVP Distribution Shape

- **Status**: Superseded by D008 after the public-hosting product boundary was clarified.
- The previous static-catalog-first conclusion assumed an internal distribution control plane and is no longer sufficient as the Registry product definition.
- Static indexes, caches, or OCI-compatible storage may still be implementation components, but they cannot replace the public service authority required for publisher identity, namespaces, package versions, and authenticated publication.

## D003 — Python-first Technology Direction

- **Status**: Accepted.
- Default to Python for Registry tooling, validation, catalog compilation/resolution, CLI behavior, and any justified reference service.
- Keep manifest and protocol truth language-neutral.
- Use JavaScript/TypeScript only for browser contracts, `client-web` Runtime/API integration, Module Federation builds, and browser-specific conformance tooling.
- Exact Python version, project manager, lock strategy, libraries, and package topology remain open until the development-foundation slice.

## D004 — First-party Source During MVP

- **Status**: Accepted.
- First-party extension source remains permanently in the relevant peer repositories rather than moving into `ext-reg`.
- Each peer preserves local extension/runtime joint development and owns the CD that contributes its technical target artifact to the shared Extension Version in the production Registry.
- Use existing first-party components as acceptance candidates without giving them a separate Registry code path.

## D005 — Long-term Extension Source Ownership

- **Status**: Accepted; the prior dedicated first-party extensions repository recommendation is superseded.
- First-party source is peer-owned to preserve the peer/extension joint-development loop.
- Third-party source remains publisher-owned in whatever repository topology that publisher chooses.
- `ext-reg` never becomes source authority for hosted extensions; it owns publication and hosting contracts.
- Source topology does not need to optimize Registry publication because every source repository publishes through the same protocol and CD boundary.

## D006 — Production Trust Boundary

- **Status**: Superseded by D008 for service topology; launch admission policy remains open.
- The service architecture must support ordinary non-reserved publishers rather than encode a first-party-only production path.
- First-party acceptance may validate the MVP, but public publisher onboarding timing and moderation gates require separate decisions.
- No design or documentation may imply that in-process Python or same-page browser extension code is sandboxed when it is not.

## D007 — Task Control Structure

- **Status**: Accepted.
- `packet.md` is the compact SVC control surface and navigation root.
- Evidence, decisions, architecture, roadmap, and acceptance each have one supporting owner file.
- Add execution-specific files only when a bounded slice starts; do not grow a second task tracker or duplicate durable truth.

## D008 — Public Multi-publisher Registry

- **Status**: Accepted.
- The product is a publicly reachable extension/package registry analogous in role to npm Registry or PyPI.
- Public consumers can discover, resolve, and download admitted packages; publishers authenticate to create and publish according to namespace ownership and Registry policy.
- InKCre first-party packages occupy a reserved namespace but use the same package model and publication protocol as other publishers.
- Publisher source and CI/CD remain outside the Registry repository. The production Registry accepts target-artifact contributions from authorized external pipelines, including multiple peer-owned CDs contributing to one Extension Version.

## D009 — PoC Before CI/CD

- **Status**: Accepted but refined by D010.
- Do not design CI/CD around an empty project skeleton.
- PoC work must test questions derived from accepted product design and High-level technical design rather than substitute for either.
- Complete DX, engineering, and CI/CD only after technical direction and minimum executable evidence exist.

## D010 — Product Design Before HLD And PoC

- **Status**: Accepted.
- Product design is the current phase and must define observable behavior, authority, concepts, workflows, lifecycle, MVP scope, and non-goals before technical design begins.
- High-level technical design follows the product design gate.
- A PoC is justified only by named uncertainty or risk in the High-level technical design.
- Project initialization beyond the existing repository/SVC/task control surface—including complete DX, engineering conventions, and CI/CD—follows those product and technical decisions.

## D011 — One Version With Multiple Technical Targets

- **Status**: Accepted.
- One deployment has one installed Extension Version shared by all peers connected to the same database.
- One Extension Version contains multiple technical targets so heterogeneous peers can consume compatible artifacts without diverging on the installed version.
- A target is identified by a technical runtime contract, not by a source repository or a special first-party code path.
- Peer-owned source repositories and CD pipelines may contribute target artifacts independently to the same Extension Version.
- D013 defines publication and coverage behavior; target identity, append authorization, conflict, and recovery behavior remain product-design questions.

## D012 — Product Design Collaboration Protocol

- **Status**: Accepted for the completed discussion phase; its review/authorization pauses are superseded by D027 for autonomous delivery.
- Read-only exploration, investigation, experiments, and reasoning proceed without waiting for authorization; task-packet maintenance is continuous.
- Discuss one bounded product question at a time and keep each review surface to the minimum information needed for a responsible decision.
- Sir's statements are product input rather than automatic authority. The agent must test them—and its own proposals—against available evidence, invariants, counterexamples, and logical consequences, preserve independent judgment, and disagree when that produces a sounder product.
- The agent may make product decisions and designs on Sir's behalf, but must expose consequential choices for proportionate review.
- Each product-design response begins with the result of the preceding question when one exists, then immediately advances exactly one next question. Do not wait for Sir to ask whether more work remains.
- Stop only when review, a product decision, or unavailable user knowledge is needed. Code, project-state mutation, commits, publication, and cross-repository changes retain their separate authorization boundaries.

## D013 — Deployment-relative Target Coverage

- **Status**: Accepted; operation scope is clarified by D021.
- An Extension Version has no producer-declared set of required targets and the Registry does not certify global target completeness.
- An authorized publisher may explicitly make a version public once it contains at least one accepted target artifact.
- A published version is an append-only collection of targets: distinct targets may be added later, but an accepted target identity and artifact digest cannot be replaced under that version.
- A consumer must resolve a compatible target before an Extension can be enabled and executed on a peer. Disabled peers do not gate installation or a future shared version change.
- Public-but-unsuitable-for-one-deployment is a valid product state; suitability is determined by the consumer's peer topology.

## D014 — Mandatory Namespaced Extension Coordinate

- **Status**: Accepted.
- Every public Extension uses one mandatory canonical `namespace/name` coordinate; there is no unscoped global package name path.
- `namespace/name` identifies the Extension product. Version identifies a release beneath it, target identifies a technical variant within that version, and artifact digest identifies exact bytes.
- Target, peer, repository, language package name, and artifact kind do not become part of the Extension coordinate.
- InKCre first-party Extensions use the reserved `inkcre` namespace. D022 fixes the canonical segment grammar.
- Existing peer-local IDs and ecosystem package names map explicitly to the Registry coordinate; they are not alternate canonical identities.

## D015 — Extension Version Scheme

- **Status**: Accepted.
- Public Extension Versions use canonical Semantic Versioning 2.0.0 without a leading `v` or build metadata.
- Pre-release versions are allowed; stable resolution must not select one unless the consumer explicitly requests or opts into pre-releases.
- Deployment installation state records one exact Extension Version, never a range or moving label.
- SemVer describes evolution of the Extension's public product/API behavior. Peer Runtime/API compatibility remains separate target metadata and cannot be inferred from the product version alone.
- Appending a new target artifact to an existing version expands distribution coverage but must implement the same already-versioned Extension behavior; it is not permission to change that version's semantics.

## D016 — Structured Technical Target Contract

- **Status**: Accepted in principle; the initial three-category condition taxonomy is superseded by D018.
- A Technical Target uses structured, machine-evaluated compatibility declarations, not an opaque label, peer name, repository name, or exact full-stack fingerprint.
- Target and peer declarations use a shared controlled vocabulary; unresolved or unknown mandatory conditions fail closed.
- Exact fields, grammar, matching algorithm, and storage representation belong to HLD and contract design after product semantics are accepted.
- Human-readable target labels may exist for display and debugging but are not compatibility or identity authority.
- The Registry validates declarations and vocabulary; the deployment consumer evaluates its participating peers' compatibility before install or upgrade.

## D017 — Bilateral Capability/Requirement Model

- **Status**: Superseded by D018 before acceptance.
- The symmetric resource model exposed internal `provides`/`requires` structure that is unnecessary at the Registry product boundary.
- Artifact facts and host dependencies both reduce to conditions under which a target can be installed on a consumer platform.

## D018 — Target Compatibility Predicate

- **Status**: Accepted.
- A producer publishes one structured Target Compatibility Contract: a machine-evaluated predicate over a consumer Platform Profile.
- The profile contains the platform's actual facilities and the integration contracts its peer accepts. Compatibility exists only when every mandatory target condition is satisfied; unknown mandatory conditions fail closed.
- Artifact/integration format, Extension Runtime/API, loader, shared modules, language/ABI, Web execution baseline/features, OS, and architecture use controlled condition dimensions when they materially affect loading or execution.
- Artifact facts such as implemented API and load format become platform-acceptance conditions for matching. Extension-specific entry points are compatibility conditions only when an accepted Runtime/API contract mandates them.
- Browser, peer, repository, and human target labels remain non-authoritative display metadata. `V8` alone is not a sufficient Web platform constraint.

## D019 — Consumer-owned Target Selection And Exact Binding

- **Status**: Accepted.
- Compatibility filtering and preference are separate. After filtering by the accepted Target Compatibility Contract, the consumer peer/runtime adapter applies a deterministic, auditable preference policy for its platform.
- Publisher priority and Registry upload/catalog order do not decide semantic preference. If several targets remain equally preferred, the adapter uses a documented stable fallback and may optionally allow an operator/user to override it with another compatible candidate; overlap is not an error.
- A successful deployment install or upgrade plan binds each participating resolution subject to the selected target identity and artifact digest while preserving one shared Extension Version.
- Existing bindings do not change merely because another target is appended to that version. Re-resolution is explicit; exact trigger and persistence shape remain later product/HLD questions.

## D020 — Authorized Platform Change Disables Incompatible Extensions Per Peer

- **Status**: Accepted.
- Peer admission and peer/runtime upgrades are higher-priority, explicit user-authorized platform operations. Before confirmation, the product discloses which Extensions will become unavailable on the affected peer.
- InKCre's existing per-peer enablement is authoritative: the operation removes only the affected peer UUID from incompatible Extensions' enabled sets. It does not globally disable them, change the shared installed Extension Version, or disturb compatible peers and bindings.
- A new peer has existing Extensions disabled by default. Re-enabling later requires compatible target resolution and a new exact binding for that peer.
- Compatible existing bindings remain stable; a platform operation does not opportunistically switch targets.
- Uncontrolled environment drift is outside the MVP product scope. Existing runtime error observability remains, but the Registry does not promise a dedicated prediction or remediation system.

## D021 — Compatibility Gates Follow Enablement

- **Status**: Accepted.
- Installing a published Extension Version creates deployment state disabled for all peers and does not require target coverage for disabled peers.
- Enabling an Extension on a peer requires that peer's runtime adapter to resolve, select, and bind a compatible target.
- An Extension version change requires coverage for every peer on which the Extension is currently enabled. Missing coverage blocks the change; MVP has no automatic disable-and-upgrade combined operation.
- Compatibility does not need to be proven for registered peers on which the Extension remains disabled. This refines `participating peer` in D013 to the enablement scope relevant to the operation.

## D022 — MVP Namespace And Publisher Boundary

- **Status**: Accepted.
- Canonical coordinates use lowercase `namespace/name`; each 1–64 character segment matches `[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?`.
- `inkcre` is operator-reserved. MVP namespace onboarding and publisher credential issuance are manual; anonymous discovery/download and scoped authenticated publication are required.
- Self-service claims, transfer, disputes, teams/SSO, and a publisher management UI are non-goals.

## D023 — Target Slot And Upload Conflict

- **Status**: Accepted.
- A producer-chosen target key is an immutable slot beneath `namespace/name@version`; it is identity/display metadata and has no compatibility semantics.
- Retrying the same target key and digest is idempotent. The same key with a different digest conflicts. A new key appends another immutable target.
- Release and target semantics cannot be overwritten after public publication; corrections use a new version.

## D024 — Minimal Release Lifecycle

- **Status**: Accepted.
- MVP states are preparing, published, yanked, and operator-blocked. Explicit publication requires at least one accepted target; published versions may append new target keys.
- Yank excludes new resolution/install/enable but does not mutate an existing deployment. Operator block may deny new download for takedown.
- Ordinary physical delete/unpublish, deprecation policy, restore UI, and advanced moderation are non-goals.

## D025 — Minimal Deployment Lifecycle

- **Status**: Accepted.
- Install records one exact published version disabled for all peers. Enable resolves and binds one compatible target/digest before adding that peer; disable unloads and clears only that peer's binding.
- Uninstall requires all peers disabled and non-running, then removes installation, bindings, and configuration without changing Registry state.
- Extension version upgrade/rollback orchestration and Extension-to-extension dependencies are not required for MVP.

## D026 — MVP Trust And Availability

- **Status**: Accepted.
- Browser and Python Extensions are trusted privileged code, not sandboxed. MVP uses scoped publisher authentication, HTTPS, and content digests; malware scanning, signatures, attestations, dependency resolution, mirrors, and advanced abuse controls are non-goals.
- Registry outage does not stop already-running code. Operations requiring an unavailable artifact fail without changing installed/enabled state; offline cold-start is not promised.

## D027 — Autonomous Delivery Authorization

- **Status**: Accepted from the current user objective.
- Product design review is no longer a blocking gate. The agent is authorized to finish product design, HLD, implementation planning/preflight, code changes, cross-repository integration, appropriate commits, repository creation, CI/CD, secret reset, and public-demo production acceptance without further review.
- `core-py` and `client-web` work must start from fresh `origin/main` feature branches in separate worktrees and must not modify the users' existing worktrees.
- The execution remains MVP-bounded: prefer mature libraries and standards, write only a few critical black-box E2E tests, and exclude speculative/security-heavy edge systems.

## D028 — MVP Service And Artifact Topology

- **Status**: Accepted after targeted PoCs.
- The public service is one Cloudflare Python Worker using FastAPI, D1 for transactional Registry metadata, and private R2 for SHA-256-addressed target manifests and file blobs.
- Python 3.13, Node 22, `uv`, `pywrangler`, Pydantic/FastAPI, Typer, and `httpx` are the selected foundation. Python 3.13 follows the Pyodide version selected by the production Worker compatibility date rather than the server peer's independent Python 3.12 runtime. Pydantic is bounded to the version with a current Pyodide wheel. A thin TypeScript Worker is the bounded fallback if the beta Python runtime later blocks production; it does not change the public contracts.
- Publisher authentication is manually provisioned namespace-scoped bearer credentials stored as hashes in D1. GitHub OIDC, Access, self-service identity, and team management are deferred.
- A canonical language-neutral target manifest owns only executable contract facts: file paths/digests, format, entry point, and compatibility. Its SHA-256 is the deployment-bound target digest. Source/build provenance belongs to the immutable Registry target association so an unchanged artifact can retry idempotently from a later application build. R2 is byte storage, not package authority.
- The public immutable artifact prefix is digest-addressed. A relative-base Module Federation remote was proven to load all cross-origin chunks from this prefix.

## D029 — Deployment Installation And Binding Model

- **Status**: Accepted.
- A new deployment installation record owns `namespace/name@exact-version` and shared configuration. A separate peer binding record owns peer UUID, target key, and exact target digest. Installation starts with no binding; binding existence means enabled; running remains volatile runtime state.
- `core-py` owns the shared database migration and install/uninstall coordination. Each peer adapter owns local compatibility, target admission, lifecycle start/stop, and its own binding transition.
- Existing artifact-local discovery may supply admitted bytes but may not create installed state. The legacy startup sync that recreates all checked-in packages as installed must be retired or isolated during migration.
- `core-py` executes only a target bundle embedded and digest-admitted by its application image. `client-web` may fetch its exact digest-pinned Module Federation bundle from the Registry.
