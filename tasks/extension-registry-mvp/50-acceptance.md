# Native Cutover Acceptance

## Purpose

The earlier generic-target MVP passed its production journey and remains useful
historical evidence. This acceptance model proves the replacement architecture:
native hosted Distributions, one shared installed Release, platform-specific
Host SDKs, one canonical deployment table, and no compatibility/binding
infrastructure left from the rejected design.

Passing unit tests or serving HTTP `200` is insufficient. Each gate asserts the
authority owner, persisted state, native consumer behavior, runtime effects,
failure residue, source/artifact identity, and rollback evidence.

## Gate 1 — Repository And Contract Shape

- Registry production code/schema/OpenAPI contain Extension/Release,
  Python-native, and MF-native concepts; they contain no `target_key`, target
  digest, generic conditions, `artifact_format`, public target manifest,
  compatibility matcher, or shared Runtime/API package.
- Core production code has one Host SDK/manager, one startup/shutdown path, one
  canonical `extensions` model, and no Registry binding manager, target catalog,
  ZIP loader, checked-in production Extension source, or image-embedded bundle.
- Web production code has one Host SDK facade and semantic state port, with no
  installation/binding manager, target matcher/profile, artifact-manifest
  loader, or `@inkcre/extension-runtime` dependency.
- Language-neutral contract truth is limited to Extension Name/Nickname,
  Release/lifecycle, native association descriptors, Host SDK identity/range,
  and observable operation errors.
- Generated OpenAPI, JSON schema, migration/schema artifact, PostgREST types,
  documentation navigation, and task evidence agree with the implemented
  shape.

## Gate 2 — Registry Native Publication

### Python journey

1. An `inkcre` namespace credential prepares an Extension Release with a typed
   Python association.
2. `uv publish`/compatible multipart uploads a normal wheel to `/legacy/`.
3. Registry archive admission verifies name/version/entry point, safe paths,
   Core Metadata, `Requires-Python`, and SHA-256 before public visibility.
4. Explicit publish exposes the exact Release descriptor, Simple HTML and JSON
   1.1, the SHA-256 file link, PEP 658 metadata sidecar, and immutable wheel
   bytes anonymously.
5. Python 3.12 `pip` selects the exact wheel from the public Simple index and
   loads its `inkcre.core.extensions` entry point.

### Module Federation journey

1. The same or another Extension Release is prepared with an MF association.
2. Publisher uploads the exact checked Remote snapshot containing native
   `mf-manifest.json`, Remote entry, and complete asset closure.
3. Registry rejects unsafe/absolute/traversing/missing manifest references,
   materializes absolute immutable `metaData.publicPath`, and publishes no
   generic manifest.
4. Anonymous browser fetch from another origin receives CORS, immutable cache,
   ETag, native manifest, Remote entry, and every referenced asset.
5. The pinned MF Host loads the manifest directly and obtains the expected
   platform-specific lifecycle export.

### Publication behavior

- Preparing is absent from public install/Remote routes.
- A Release can publish with either native association and append only a
  previously absent format or Python filename later.
- Same natural key plus identical bytes/metadata is idempotent; changed bytes or
  metadata is `409` and leaves the original association unchanged.
- `published → yanked → published` preserves exact descriptor and bytes; Simple
  links carry/remove the yank reason. Normal new selection excludes yanked.
- Operator block prevents new reads without deleting audit metadata.
- Failed archive validation, R2 write, D1 transaction, or publish leaves no
  public partial Release; private staging residue is bounded/collectable.
- Missing `Content-Length`, oversized, chunked, malformed multipart, duplicate
  ZIP path, traversal, compression abuse, or digest mismatch fails closed.

## Gate 3 — Six First-party Python Distributions

- `github`, `learn_english`, `mail`, `rss`, `telegram`, and `twitter` each build
  a normal wheel from `core-py`, with complete native dependencies,
  `Requires-Python`, source association metadata, and a standard entry point.
- All six use PEP 420 packages `extensions.<id>` without owning
  `extensions/__init__.py`.
- A clean Python 3.12 environment installs every wheel from Registry Simple;
  no Core image source-tree fallback is present.
- Entry-point loading against every declared Core Host SDK line initializes the
  exact expected Source/Resolver identities and catches direct-internal-import
  drift before publication.
- Core's root dependency set contains only application-owned dependencies;
  Extension-only dependencies live in the wheels.

## Gate 4 — Canonical Deployment State

The exact deployed contract is:

```text
extensions(name, version, enabled[], nickname, config, config_schema)
```

- Row presence means installed; installation creates `enabled=[]`.
- All Peers read one exact Release version from the same row.
- `enabled[]` is the per-Peer intent set; there is no Distribution/binding row.
- Peer enable/disable is one atomic database operation and cannot lose another
  Peer's concurrent membership update.
- Host SDKs consume a semantic state port; SQLModel/PostgREST generated types do
  not cross the Extension API.
- Install/config/version updates/uninstall use one management model and canonical
  Extension Name.
- Uninstall requires no enabled/running Peer and removes only the canonical row.

## Gate 5 — Core Host SDK Lifecycle

For one published wheel and then all six:

1. install exact Release; verify disabled and no local runtime effects;
2. enable Core Peer; verify Host SDK range before byte acquisition, native
   installer selection, entry-point class, validated `ExtensionBase.config`,
   `on_start`, routes/Sources/Resolvers, then atomic enabled intent;
3. update config through the Host SDK; invalid/failed persistence leaves runtime
   and database unchanged;
4. disable; verify `on_close`, publication/resource cleanup, then enabled intent
   removal;
5. cold restart an enabled Release; verify exact re-acquisition and runtime
   restoration;
6. uninstall after all Peers are disabled.

Failed range, Simple selection, dependency plan, wheel admission, entry point,
`on_start`, persistence, or Registry availability must not create enabled
intent or partial runtime effects. Failed cold restore retains installed version,
config, and enabled intent while readiness/runtime reports the failure. An
already imported Extension upgrade/rollback follows the tested restart-required
path rather than pretending Python modules can be safely hot replaced.

## Gate 6 — Web Host SDK Lifecycle

1. install an exact Release with no Web runtime effects;
2. enable current Web Peer; verify `@inkcre/core` range before Remote fetch,
   native manifest URL registration, `initialize → activate`, then atomic
   enabled intent;
3. render the real Twitter contribution through direct `@inkcre/core` APIs;
4. reload/cold start from the shared row and re-resolve the native manifest;
5. disable through `deactivate → dispose`, then enabled intent removal;
6. update config and uninstall through the one semantic management surface.

There is no target/binding UI or Peer-target selection. A lifecycle or network
failure leaves enabled intent consistent with the operation ordering, and one
Peer's toggle cannot erase another's enabled membership.

## Gate 7 — Shared-version And Native-format Behavior

- `inkcre/twitter@<version>` is one installed product Release.
- Core and Web read the same database version while consuming different native
  Distribution bytes and metadata.
- Missing Python blocks only Core enable/preflight; missing MF blocks only Web.
  It does not make the Release intrinsically incomplete.
- Upgrade/rollback is rejected while any Peer remains enabled. After explicit
  disablement, one shared version changes; every Peer must pass its own Host SDK
  preflight before it can be re-enabled. A rejected version change preserves the
  old version and enabled set.
- A newly added Peer begins disabled. Authorized Host SDK upgrade may disclose
  and disable only incompatible Peers; no uncontrolled browser drift remediation
  is promised.
- New install/upgrade requires `published`. An already installed exact `yanked`
  Release may cold-restore/enable with warning if native bytes remain; operator
  block or unavailable bytes fail without rewriting durable intent.

## Gate 8 — Clean Reset And Data Preservation

### Registry

- A fresh D1 schema contains only native Registry records and starts with the
  reserved namespace/rotated credentials required for publication.
- A fresh R2 bucket contains only newly published native wheels, metadata, MF
  manifests/assets, and bounded private staging.
- Old blackbox, old Twitter `0.1.0`, target rows, canonical target manifests,
  and generic blobs are absent rather than migrated or tombstoned.

### Deployment

- The append-only Core migration targets exactly old `extensions`,
  `extension_installations`, and `extension_peer_bindings`, then creates one
  empty canonical relation.
- A before/after diagnostic proves all unrelated tables, row counts, ownership,
  ACL, client records, Sources, Blocks, and schema authority are unchanged.
- Fresh init, repeated init, migration from the previous demo head, neutral
  schema export/restore, PostgREST, `/readyz`, and generated client contract all
  pass.
- After cutover every Extension is explicitly reinstalled and every Peer starts
  disabled.

## Gate 9 — Delivery Identity And Operations

- CI checks frozen dependencies, format/lint/type/unit/integration/build,
  Worker bundle, six wheels, native manifest closure, database contract, and
  full peer checks.
- Publication consumes the exact artifact produced by a successful protected-
  main check; delivery never rebuilds wheel/Remote bytes.
- Source repository/revision, workflow/run, native filename or MF manifest, R2
  object, D1 association, deploy revision, and public observation are traceable.
- PR/preview artifacts cannot publish canonical Releases or mutate the public
  demo.
- Registry, Core, Web, database reset, and publication order is rehearsed with
  explicit maintenance effects and no hidden dual-write period.
- Read-only public smoke validates livez, exact descriptors, Simple HTML/JSON,
  wheel hash/metadata, MF manifest/assets/CORS/cache, D1 records, and R2
  prefixes.

## Gate 10 — Rollback And Completion

- Before cutover, diagnostics capture the old Registry bindings/resources,
  three Extension relations, and exact Core/Web artifacts.
- Before new user mutations are admitted, rollback can rebind old D1/R2,
  redeploy old exact artifacts, and restore the three Extension relations as one
  coherent unit.
- Old resources are deleted only after the rollback window and native journey
  pass.
- Repository search plus public/deployment observations show no production
  legacy, target, binding, embedded-bundle, or shared Runtime/API path.
- The task is complete only after the production-like lifecycle ends with the
  intended installed/enabled/running/config state and all failures have
  machine-readable evidence.
