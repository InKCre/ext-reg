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

- **Status**: Superseded by D031; the scoped identity remains, but it is the Extension Name rather than a separate Coordinate concept.
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
- InKCre's existing per-peer enablement is authoritative: the operation removes only the affected peer UUID from incompatible Extensions' enabled sets. It does not globally disable them, change the shared installed Extension Version, or disturb compatible peers.
- A new peer has existing Extensions disabled by default. Re-enabling later requires that Peer Host SDK to preflight and consume its native Distribution for the exact installed Release.
- Compatible enabled Peers remain enabled; a platform operation does not rewrite the installed Release or persist a Distribution selection.
- Uncontrolled environment drift is outside the MVP product scope. Existing runtime error observability remains, but the Registry does not promise a dedicated prediction or remediation system.

## D021 — Compatibility Gates Follow Enablement

- **Status**: Accepted invariant; native execution mechanism superseded by D049
  and D052.
- Installing a published Extension Version creates deployment state disabled for all peers and does not require native Distribution availability for disabled peers.
- Enabling an Extension on a peer requires that Peer Host SDK to preflight and consume a compatible native Distribution before adding the Peer UUID.
- Compatibility does not need to be proven for registered peers on which the Extension remains disabled. This refines `participating peer` in D013 to the enablement scope relevant to the operation.

## D022 — MVP Namespace And Publisher Boundary

- **Status**: Accepted.
- Canonical coordinates use lowercase `namespace/name`; each 1–64 character segment matches `[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?`.
- `inkcre` is operator-reserved. MVP namespace onboarding and publisher credential issuance are manual; anonymous discovery/download and scoped authenticated publication are required.
- Self-service claims, transfer, disputes, teams/SSO, and a publisher management UI are non-goals.

## D023 — Target Slot And Upload Conflict

- **Status**: Superseded by D031; format-native Distributions replace public target slots.
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

- **Status**: Superseded by D031.
- A new deployment installation record owns `namespace/name@exact-version` and shared configuration. A separate peer binding record owns peer UUID, target key, and exact target digest. Installation starts with no binding; binding existence means enabled; running remains volatile runtime state.
- `core-py` owns the shared database migration and install/uninstall coordination. Each peer adapter owns local compatibility, target admission, lifecycle start/stop, and its own binding transition.
- Existing artifact-local discovery may supply admitted bytes but may not create installed state. The legacy startup sync that recreates all checked-in packages as installed must be retired or isolated during migration.
- `core-py` executes only a target bundle embedded and digest-admitted by its application image. `client-web` may fetch its exact digest-pinned Module Federation bundle from the Registry.

## D030 — Post-acceptance Review And Remediation Protocol

- **Status**: Accepted.
- Functional production acceptance remains evidence, but the MVP is reopened for product, architecture, implementation, and delivery review.
- Review proceeds in adjacent problem batches: evidence and diagnosis first, one bounded design decision surface per conversation round, then an explicit impact handshake before implementation remediation.
- Sir's findings and prior agent decisions have equal evidentiary status: both must be checked against executable facts and product invariants.
- The task packet owns the batch queue and diagnosis; accepted changes must update their canonical implementation or durable design owner rather than leaving corrections only in review notes.

## D031 — Canonical Extension State And Format-native Distributions

- **Status**: Accepted; supersedes D014 terminology, D023 target slots, and D029's parallel installation/binding tables.
- `inkcre/twitter` is one canonical Extension Name. Its ownership scope is part of the name rather than a separate Extension Coordinate concept. `Twitter` is an Extension Nickname.
- One shared `extensions` record owns the exact installed Extension Release version, Extension Nickname, shared configuration/schema, and the existing enabled Peer UUID set.
- The existing `extensions` relation is migrated directly. Parallel `extension_installations`, `extension_peer_bindings`, target keys, and persisted Distribution/content digests are removed.
- An enabled Peer resolves a compatible format-native Extension Distribution on enable or cold start. The product does not promise to retain the previously selected Distribution bytes across cold starts; all Distributions under one Release must preserve that Release's product semantics.
- There is no universal public cross-format Distribution ID and no capabilities digest. Python packaging and Module Federation own their native Distribution identity and resolution surfaces. Opaque Registry row IDs and content digests may remain internal implementation and integrity details.

## D032 — Runtime-owned Execution Orchestration

- **Status**: Accepted only as an ownership direction; the universal lifecycle implication is withdrawn by the Batch 02 review.
- Each platform-specific Extension Host SDK, not a Peer integration adapter, owns its own enable/disable/cold-start/shutdown sequencing, lifecycle state, failure compensation, and consistency policy around persisted enabled intent.
- Platform-specific Runtime implementations own their format-native Distribution Consumers. The Runtime Adapter is not the Registry client, Distribution loader, or workflow manager.
- The Host SDK uses a semantic deployment-state port and does not know database tables, PostgREST, concrete enabled-column storage, or transaction implementation.
- Runtime integration is separate from Extension Developer Kits, build tooling, conformance tooling, and publication/CD clients; the Runtime Adapter has no development-time packaging or publishing responsibility.
- The likely top-level integration product is a platform-specific Extension Host SDK embedded by a Peer. It manages Extension discovery/loading/lifecycle but does not mediate an Extension's direct use of Core APIs. A single language-neutral lifecycle, public `ExtensionScope`, or common registration model is not implied.

## D033 — Separate Extension Host API Profiles

- **Status**: Accepted in direction; concrete Core Python and Client Web API shapes remain under Review Batch 02.
- Core Python and Client Web use separate Extension API Profiles. A profile owns its Host SDK's Distribution Consumer/protocol/format semantics, Extension entry shape, lifecycle, compatible Peer implementation surface, and configuration semantics. A profile is not assumed to be a standalone SDK package or restricted public API.
- Distribution Format remains a native Registry and storage fact, but is not a parallel generic compatibility axis for the deployment. The Host SDK already implements the formats and metadata admitted by its Extension API Profile.
- A Distribution declares its compatible Peer/Host SDK implementation version through format-native or Registry pre-download metadata. Its Host SDK evaluates that requirement before executable bytes are acquired or loaded.
- Language-neutral truth is limited to Extension/Release identity, Distribution descriptors, Peer/Host SDK compatibility identity/range, deployment state distinctions, and observable operation guarantees. Python and Web do not implement one common callable Extension API or lifecycle state machine.
- The Host SDK manages Extension loading and lifecycle; Extensions access Peer implementation APIs directly rather than through the Host SDK and may currently import internal modules. Core's explicit `on_close` is not replaced by generic deferred cleanup, and there is no `ExtensionScope` concept.
- Because Core Python has no independently versioned public Extension API package, its pre-download compatibility claim must currently reference a producer-tested compatible Core Peer implementation/version. Creating a narrower stable public API is a separate, unaccepted future decision.

## D034 — Peer/Host SDK Version Is The Extension API Version

- **Status**: Accepted.
- There is no independent cross-platform or per-Peer Extension API version. The authoritative implementation version of the Peer/Host SDK against which a Distribution is built and tested is that Distribution's Extension API compatibility version.
- Each Peer repository owns and releases its implementation version. The Registry preserves and exposes producer-declared compatible version ranges but does not mint, translate, or synchronize another API version.
- Importing Peer internals remains allowed. The producer owns the resulting compatibility claim and must narrow or update its declared range when those dependencies are not stable.
- Core Python currently anchors compatibility to the `core-py`/embedded Host SDK implementation version; Client Web anchors it to the `@inkcre/core`/embedded Host SDK implementation version.

## D035 — Producer-declared Host SDK Compatibility Ranges

- **Status**: Accepted.
- Distribution producers declare compatible Peer/Host SDK SemVer ranges by default; exact version constraints remain available when an Extension relies on fragile internals.
- While Peer/Host SDK versions remain pre-1.0, PATCH releases preserve Extension compatibility and MINOR releases may break it. Each Peer repository owns compliance with this release rule.
- The Registry validates range syntax and exposes the declaration before download. The producer owns the truth of its range, and the Host SDK evaluates it against its authoritative implementation version.

## D036 — Format-native Entry Handshake Is The Extension API

- **Status**: Accepted.
- An Extension API does not require a standalone SDK package or restricted public Core surface. The minimum Extension API is the versioned Host SDK–Distribution contract: native Distribution metadata and entry discovery, expected entry shape, Peer-specific lifecycle calls, and Host SDK implementation-version compatibility.
- Core Python uses a standard Python package entry point to locate its Extension class. Client Web uses a documented Module Federation exposed module/default export. Hard-coded Python module paths derived from Extension Name are not Registry identity or discovery authority.
- Python and Web lifecycle/entry shapes remain intentionally independent. After loading, an Extension may continue to import and call arbitrary Peer implementation APIs directly.

## D037 — Core ExtensionModel Does Not Cross The Extension API

- **Status**: Superseded by D038. The concrete persisted SQLModel still does not
  cross the Extension API, but this conclusion understated the Host SDK's model
  authority.
- Core Python preserves its explicit `on_start/on_close` lifecycle and may expose Peer-specific runtime objects such as FastAPI, but the persisted `ExtensionModel` is not a lifecycle argument or Extension API type.
- The Host SDK obtains persistence through its Peer integration and supplies validated configuration plus any deliberately supported state through the Extension API.
- An Extension may still voluntarily import Core database internals. That producer-chosen dependency does not justify making the concrete database row mandatory for every Extension Distribution.
- Deployment state, Extension-private persistent state, and process-local runtime state must remain distinct; `state` is not accepted as one undifferentiated mutable object.

## D038 — ExtensionBase Owns The Core Extension-facing Model

- **Status**: Accepted; Extension-level persistent state is excluded by D042.
- A Core Extension inherits the Host SDK's `ExtensionBase`. `ExtensionBase` is
  the Extension-facing API surface and owns the semantic model and operations
  through which the Extension reads validated configuration.
- The Host SDK therefore owns the authority for the Extension-facing model,
  validation, mutation semantics, and lifecycle visibility. The Peer supplies a
  persistence implementation behind that model; the Extension does not receive
  a database row or storage adapter.
- The current SQLModel table class and the Host SDK model are not the same
  authority. A concrete database record remains a private persistence
  representation and may change without changing the Extension API. Reusing the
  name `ExtensionModel` for both would obscure this boundary.
- Before `on_start`, the Host SDK binds the loaded Extension class to its
  installed identity and persisted values. `on_start/on_close` remain explicit,
  while config access occurs through inherited `ExtensionBase` behavior
  rather than a public `ExtensionScope` or a lifecycle argument containing the
  persistence record.
- Installation version and per-Peer enabled intent remain Host SDK-managed
  deployment state, not arbitrary Extension-writable config/state.

## D039 — Core Config And State Access Policy

- **Status**: Superseded in part by D042. The config policy remains accepted;
  the proposed Extension-level state API is excluded from this MVP.
- `ExtensionBase` exposes validated configuration as read-only to Extension
  code. User/deployment management paths may update configuration through the
  Host SDK, which owns validation, persistence, and live refresh semantics.
- `ExtensionBase` exposes deliberately supported Extension-private persistent
  state as readable and writable to Extension code. Process-local objects remain
  ordinary Extension implementation state and do not use this persistence API.
- This asymmetry is an authority and mutation-policy decision, not a claim that
  writable configuration would become indistinguishable from state. `config`
  and `state` are already separate semantic concepts, and a future writable
  config operation would not by itself collapse them.

## D040 — Extension State Is Deployment-shared

- **Status**: Deferred by D042. If Extension-level persistent state is introduced
  in a future product task, deployment-wide scope is the accepted direction, but
  no such capability is added in this MVP.
- Extension persistent state is owned by the Extension and shared across the
  whole deployment. Every enabled instance/Peer for the same installed
  Extension observes the same logical state through its Host SDK.
- Shared state is a deliberate cross-Peer coordination and failover mechanism.
  For example, one Core instance can persist synchronization progress `25`, and
  another instance can resume from `25` after the first stops.
- Disable, process restart, and Peer replacement preserve state. Uninstall
  removes it according to the Extension installation lifecycle. Process-local
  caches, connections, and handles remain ordinary non-persistent implementation
  state and are not included.
- Concurrency control is Core/Peer implementation responsibility. Revisions,
  locks, transactions, compare-and-set tokens, retries, or scheduling policy are
  not exposed as required Extension API concepts.

## D041 — Core Hides Shared-state Concurrency

- **Status**: Deferred with Extension-level state by D042; existing Source-state
  concurrency remains owned by Core and outside Registry MVP scope.
- `ExtensionBase` exposes semantic config/state operations and their documented
  success/failure behavior. Extension code does not coordinate database
  concurrency and does not receive persistence revisions, locks, transactions,
  or storage-specific conflict tokens.
- Core owns the consistency of deployment-shared state across Peer instances and
  may implement it with database transactions, serialization, internal
  compare-and-set, single-writer scheduling, or another mechanism appropriate to
  the operation. Those choices are Core implementation details.
- This does not make arbitrary Extension-level business mutations mergeable by
  magic. The Core Extension API must offer operations whose atomic boundary is
  meaningful, while the Extension supplies its domain transition through that
  API rather than assembling a storage protocol itself.

## D042 — No Extension-level Persistent State In Registry MVP

- **Status**: Accepted; closes Review Batch 02.
- Current `extensions` and Registry installation records have no persistent
  Extension-level state, and `ExtensionBase` has no state API. This review does
  not add either capability.
- Existing deployment-shared `sources.state` and `SourceBase.get_state/set_state`
  continue to own Source-instance cursors and checkpoints. Their semantics and
  concurrency are Core responsibilities, not Registry MVP work.
- Core's Extension API remediation is limited to keeping the persisted SQLModel
  private, exposing validated read-only config through `ExtensionBase`,
  preserving explicit `on_start/on_close`, and using format-native entry
  discovery. Extension-level state requires a separate product task backed by a
  use case that is not already owned by Source or another domain resource.

## D043 — Format-native Registry Distribution Surfaces

- **Status**: Accepted; opens Review Batch 03.
- One common Registry control plane owns Extension Name, Extension Release,
  publisher authority, and release lifecycle. It associates a Release with one
  or more format-native Distributions.
- Python Distributions are exposed through the Python Packaging Simple
  Repository API with wheel/core metadata. Web Distributions are exposed as
  native Module Federation `mf-manifest.json`, remote entry, and referenced
  assets.
- Host SDKs use their native Distribution Consumer instead of parsing one
  cross-format public target manifest. Python uses packaging/install/entry-point
  machinery; Web uses the Module Federation Host.
- Generic file manifests, object IDs, and content digests may remain internal
  Registry storage, integrity, and audit mechanisms. They are not public
  cross-format Distribution identity or a required consumer protocol.

## D044 — Core Host SDK Acquires Python Distributions Online

- **Status**: Accepted.
- On enable and cold restore, the Core Host SDK uses its Python Distribution
  Consumer to resolve and acquire a compatible wheel for the exact installed
  Extension Release from the Registry Simple API, then discovers the Extension
  through its package entry point.
- Peer CD publishes first-party wheels to the Registry but does not embed custom
  Extension ZIP bundles, target catalogs, or Registry-owned Distribution bytes
  in the Core application image. The current embedded-bundle path is withdrawn.
- Host-local installed files and caches are replaceable execution material, not
  deployment authority or a promise to retain an earlier Distribution. Registry
  unavailability may block enable or cold restore without rewriting installed
  version or enabled intent.
- Extensions remain trusted privileged in-process code. Dependency environment
  construction and cleanup are separate Host SDK implementation questions, not
  reasons to return Distribution hosting to Peer CD.

## D045 — No Registry-defined Python Environment Model

- **Status**: Accepted.
- Running in one interpreter and importing Core internals is the intended trusted
  Python Extension model, not a defect or missing security boundary.
- Python compatibility and dependency declarations remain native:
  `Requires-Python` for interpreter versions, wheel tags for Python/ABI/platform,
  `Requires-Dist` and markers for dependencies, and the Registry-associated Core
  Host SDK range for the Extension API.
- The standard Python installer evaluates those declarations before entry-point
  loading. Dependency conflicts are ordinary installation failures owned by
  Core's Distribution Consumer; the Registry does not invent an environment,
  isolation, overlay, or dependency-resolution abstraction.
- Filesystem layout, caching, cleanup, and the concrete installer invocation are
  Core implementation details and require no Registry product decision.

## D046 — Producer Metadata Associates Native Distributions

- **Status**: Accepted in direction; exact source-field spelling remains an
  implementation contract.
- A producer declares the canonical Extension Name and Extension metadata in its
  format-native source project configuration. Python uses a normalized custom
  `pyproject.toml` tool table alongside standard `[project]` metadata and entry
  points; Web uses the corresponding package/build metadata consumed by its
  publisher tooling.
- The native Python project name and MF federation/build name remain
  format-specific identifiers. They need not equal the namespaced Extension Name
  and are not transformed into a universal Distribution ID or target key.
- Publisher tooling reads the custom source metadata, verifies it against the
  built wheel or MF manifest, and submits the association to the Registry. The
  Registry then links the native Distribution surface to the declared Extension
  Release.
- A Python `[tool.*]` table is build/publish input and is not assumed to appear
  automatically in wheel Core Metadata. Runtime consumers do not need it: they
  start from the installed Extension Name/Release and receive the associated
  native Distribution from the Registry.

## D047 — Native Distribution Version Congruence

- **Status**: Accepted.
- Every native Distribution associated with an Extension Release implements the
  same product version as that Release. Python project releases, Web/MF package
  metadata, and the parent Extension Release do not evolve independent version
  lines.
- Format-native normalization is not a second product version. Stable
  `MAJOR.MINOR.PATCH` versions are literally equal. A Python pre-release may use
  the standardized PEP 440 spelling corresponding to an explicitly supported
  SemVer pre-release spelling; unsupported or ambiguous mappings are rejected.
- Publisher admission verifies this congruence before association. A mismatch
  cannot be published as another Distribution of the Release.

## D048 — Solution-first Batched Review

- **Status**: Accepted; supersedes D012's one-question-per-round rule and
  refines D030.
- Exploration, diagnosis, and solution design are agent responsibilities. The
  agent must use evidence and independent judgment to produce a coherent
  recommended state diff before asking Sir to review it.
- Adjacent small decisions are grouped into one cognitively bounded review
  batch with trade-offs, failure behavior, and blast radius. Sir is the
  reviewer of the proposed solution, not the source from whom the solution is
  elicited one field or mechanism at a time.
- A round begins with the previous result, then presents the next complete
  solution batch. Stop only for a material product choice, missing user-owned
  information, or a separate authorization boundary.

## D049 — Native Distribution Registry Architecture

- **Status**: Accepted; closes Review Batch 03 and supersedes the generic target
  architecture in D011, D013, D016, D018, D019, and D028 while preserving their
  still-applicable one-Release, deployment-relative-coverage, publication, and
  authority invariants.
- One small Registry control plane owns Extension Name/Nickname, Extension
  Release, publisher authority, lifecycle, provenance, and typed native
  Distribution associations. It does not expose target keys, generic
  compatibility conditions, `artifact_format`, a capabilities digest, or a
  canonical cross-format target manifest.
- Python uses a standards-based Simple Repository read surface and
  PyPI-compatible upload surface. Wheel/Core Metadata, `Requires-Python`,
  `Requires-Dist`, tags, and a standard Extension entry point remain native
  authority. Module Federation uses one immutable native manifest/Remote asset
  snapshot per Release in the MVP.
- Producer source metadata associates each native Distribution with Extension
  Name, Nickname, the parent Release version, Host SDK identity, and the
  producer-declared Host SDK SemVer range. Registry admission verifies native
  metadata and version congruence before publication.
- Source repository, revision, and build identity belong to each native
  Distribution association, not the parent Release. Independent Core and Web
  pipelines may append different formats to the same Release without pretending
  they share a source revision; a same-format retry must preserve its own
  association provenance.
- A Release may publish after one native Distribution is ready and may append a
  previously absent native format later. Existing native associations are
  immutable; Python may append distinct native wheel files for the same project
  release. There is no producer-declared required-format set.
- Registry-managed storage hosts all Distribution bytes. Peer CD uploads but is
  not the production byte-availability authority. Internal hashes, object keys,
  and upload sessions are integrity/storage details rather than public
  Distribution identity or deployment state.
- Platform Host SDKs read the exact Release descriptor, check their own declared
  compatibility range before executable bytes, delegate to their native
  Distribution Consumer, and run their profile-specific lifecycle. No peer
  binding or Distribution digest is persisted.

## D050 — Clean Native Cutover And Demo-state Reset

- **Status**: Accepted; closes Review Batch 04 and authorizes local
  cross-repository implementation plus a later clean public-demo cutover. Git
  commits, pushes, releases, and concrete delivery actions retain their separate
  exact-object authorization gate.
- Use one coordinated maintenance cutover and remove all legacy/parallel
  Registry paths. Do not build dual-write, compatibility-facade, shadow-table,
  or embedded-artifact fallbacks.
- All six retained Core first-party Extensions become normal Registry-hosted
  wheels. Client Web's first-party Extension remains peer-owned and publishes a
  native MF Remote snapshot. No retained first-party Extension executes from
  application-image source or a custom Registry ZIP bundle.
- The deployed Registry is a public demo without authoritative production data
  or secrets. Its D1 catalog/credentials/migration state and R2 bytes may be
  recreated from a clean native schema; the old Twitter `0.1.0`, blackbox package,
  target rows, and generic blobs need not be migrated, tombstoned, or preserved.
- Deployment Extension state is also disposable for this cutover: replace the
  old `extensions`, `extension_installations`, and `extension_peer_bindings`
  contents with one empty canonical `extensions` relation. Other application
  database data remains out of scope. After cutover, installation is explicit
  and every Peer starts disabled.
- Preserve protected-main/exact-SHA/frozen-artifact governance while deleting
  checks, packages, workflows, and delivery coupling that exist only for the
  rejected target/binding/shared-Runtime architecture.

## D051 — Native-distribution PoC Constraints

- **Status**: Accepted from executable evidence; closes the HLD risk-PoC gate.
- Python Extensions are ordinary wheels contributing packages below the shared
  PEP 420 namespace `extensions`. Each wheel exposes one standard
  `inkcre.core.extensions` entry point. No wheel or Core image owns an
  `extensions/__init__.py`, and existing Source/Resolver module identities stay
  unchanged.
- MVP Python admission is wheel-only. Source distributions may be added later
  through the same native Python packaging surface, but the Registry does not
  build arbitrary publisher source or expose an unproved sdist execution path
  during this cutover.
- A wheel is not admitted merely because it builds. Its release gate must load
  the entry point and initialize its contributions against each declared
  compatible Core Host SDK line. This mechanically enforces the producer's Host
  SDK range without inventing a Registry compatibility DSL.
- The Web producer emits the native `mf-manifest.json` plus its closed asset
  set using relative build paths. At admission, the Registry validates that
  closure and materializes only the native manifest's
  `metaData.publicPath` as the immutable absolute Registry release prefix.
  Cross-origin loading uses that native manifest directly; no InKCre target
  manifest or runtime matcher is introduced.
- Python Worker upload endpoints require `Content-Length`, reject chunked
  bodies, and cap the entire multipart request at 20 MiB. The bounded file stays
  in memory because Python Workers cannot use Starlette's thread-backed spool
  path. Larger or streaming uploads are a post-MVP transport concern.
- These constraints were proved against six real Core Extensions, the pinned
  Web MF producer/Host versions, and the actual Python Worker ASGI stack. The
  reproducible procedures and failure evidence are owned by
  [`work/16-native-distribution-pocs.md`](work/16-native-distribution-pocs.md).

## D052 — MVP Version Changes Require All Peers Disabled

- **Status**: Accepted as the simplest fail-closed implementation of D023; it
  narrows, rather than automates, the earlier enabled-Peer preflight design.
- Installation still creates one exact Release with `enabled=[]`. Changing that
  installed version, including rollback, is rejected while any Peer UUID remains
  enabled. The user disables affected Peers explicitly, changes the one shared
  version, then re-enables each Peer through its own native Host SDK preflight.
- This guarantees that a version write cannot race independent Peer consumers,
  requires no cross-Peer orchestration service, and introduces no hidden
  disable-and-upgrade side effect. A future product task may permit atomic
  enabled-Peer preflight and coordinated version change without altering the
  Registry Release model.

## D053 — Native Cutover Does Not Reuse Twitter 0.1.0

- **Status**: Accepted from immutable-release and cross-Peer version invariants.
- The old demo Registry may be deleted, but that does not make a historically
  published Extension Name/version reusable. Native Twitter Python and MF
  Distributions both publish under the new compatible Release
  `inkcre/twitter@0.1.1`; their independent pipelines append to that same
  Release.
- The other five Core-only first-party Extensions may publish their first native
  wheel as `0.1.0`. Any later source or Distribution-byte change requires the
  corresponding Extension Release version to change before CD can publish it.
