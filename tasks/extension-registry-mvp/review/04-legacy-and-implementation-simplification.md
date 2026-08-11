# Review Batch 04 — Legacy And Implementation Simplification

## Scope

- Explain why the implementation introduced a `legacy extension` path and inventory every compatibility seam it added.
- Decide whether to migrate, replace, or remove the legacy path.
- Audit where the MVP reduced features but retained avoidable implementation and CI/CD complexity.
- Produce coherent remediation batches that reduce components, duplicated contracts, workflows, and migration burden.

## Status

Accepted redesign. Functional production acceptance does not exempt this
implementation from simplification. Sir authorized local cross-repository
implementation and a clean public-demo cutover; commits, pushes, releases, and
concrete delivery actions still require their exact-object authorization gate.

## Diagnosis

The `legacy extension` path was introduced for two initially defensible reasons:

1. add Registry installation/binding tables without reinterpreting the existing
   `extensions` relation or risking current first-party configuration and
   enablement;
2. preserve Core's build-time trust boundary by admitting Registry metadata only
   when matching target bytes were embedded in the application image.

Both reasons disappeared under the accepted redesign. The existing `extensions`
relation is now the destination authority, and Registry-hosted native Python
Distributions replace image-embedded custom bundles. Keeping both paths would be
pure transition debt.

The debt is concrete:

- Core production has two managers and startup/shutdown paths: approximately
  584 lines in the original manager plus 1,026 lines in the Registry manager;
- Web production has approximately 589 lines in its original Extension model
  plus 703 lines in the Registry manager;
- the deployment database has `extensions`, `extension_installations`, and
  `extension_peer_bindings` representing overlapping product state;
- Core builds, verifies, copies, imports, and publishes a custom ZIP bundle even
  though the Registry product is supposed to host it;
- Web and Core consume shared generic matcher/lifecycle packages that the new
  platform-specific Host SDK boundary rejects;
- ext-reg CI builds and tests Python plus a TypeScript Runtime/API package,
  cross-language fixtures, a generic target manifest, and compatibility
  matrices that no longer belong to the product;
- production discovery currently includes the test-only `inkcre/blackbox`
  Extension, proving that delivery smoke data leaked into the public catalog.

## Integrated Recommendation

### 1. Perform A Coordinated Hard Cutover, Not Long-lived Dual Write

Use one planned maintenance window to move Registry, database, Core, and Web to
the accepted model together. Do not introduce another compatibility facade,
dual-write period, shadow table, or translation service.

This is the smallest durable implementation. It trades a short, announced MVP
maintenance window for avoiding months of two schemas, two APIs, two runtime
managers, and ambiguous ownership. The cutover is user-authorized platform work,
so temporarily unavailable Extensions are preferable to hidden divergent state.

Before the window, build and publish native Distributions for every Extension
that the production migration will retain. First-party source remains in its
Peer repository; publication does not move source into `ext-reg`.

### 2. Reset And Consolidate Deployment State Into One Relation

The destination relation is conceptually:

```text
extensions
  name          canonical Extension Name, primary key (`inkcre/twitter`)
  version       exact Extension Release
  enabled[]     Peer UUIDs
  nickname      human-facing Extension Nickname
  config
  config_schema
```

`extension_installations` and `extension_peer_bindings` are removed. The
concrete SQLModel is private persistence; the Host SDK consumes a semantic state
port as accepted in Batch 02.

The public-demo deployment contains no authoritative Extension configuration or
enablement that must survive. The cutover therefore resets only Extension-owned
deployment state:

1. record a diagnostic snapshot for rollback evidence, not data migration;
2. drop the old `extensions`, `extension_installations`, and
   `extension_peer_bindings` relations;
3. create the single canonical `extensions` relation empty;
4. update the database contract, readiness checks, generated client types, and
   neutral schema artifact in the same release;
5. reinstall accepted Extension Releases explicitly after cutover; every Peer
   starts disabled.

Other application tables and user/domain data remain untouched. Tests prove the
reset targets exactly these three relations and cannot broaden into a database
reset. There is no ID mapping, merge algorithm, conflict resolver, or residual
legacy fallback to maintain.

### 3. Package Every Retained First-party Extension Natively

Core currently has six checked-in first-party Extension directories. Every one
that remains installed after cutover must become a normal wheel project with:

- standard project name/version/dependencies/`Requires-Python`;
- the Core Extension entry-point group;
- normalized `[tool.inkcre-extension]` association metadata;
- version equal to its Extension Release;
- a peer-owned build/test/publish job using the same Registry protocol as a
  third-party publisher.

Extension-specific dependencies leave Core's root application dependency list
and move into each Distribution. The production Core image no longer copies the
`extensions/` source tree or any Registry bundle/catalog. Local joint development
may continue to use editable/local packages through a development-only command;
that path is not production installation authority.

Client Web currently has one checked-in first-party Remote. It remains a
workspace for joint development but publishes a native MF snapshot with the
same Extension Release version and association metadata.

This prerequisite is deliberately comprehensive. Keeping one unpublished
built-in package would recreate the legacy path under another name. An operator
may instead uninstall a disabled Extension before migration, but cannot retain
it through image-local execution.

### 4. Converge Each Peer On One Host SDK

Core keeps one Extension Host facade and separates only deep internal modules:

```text
Core Extension Host
  -> semantic deployment-state store
  -> Registry Release reader
  -> Python Distribution Consumer
  -> entry-point loader
  -> Core ExtensionBase + on_start/on_close runtime
```

Remove `RegistryExtensionManager`, artifact sync as installation, local target
catalog/admission, ZIP import machinery, and double startup/shutdown loops. Keep
the valuable runtime publication handle, running-map correction, reversible
route/source/resolver cleanup, validated config behavior, and existing explicit
Core lifecycle.

Web likewise exposes one Extension Host facade:

```text
Web Extension Host
  -> semantic deployment-state port
  -> Registry Release reader
  -> Module Federation Host
  -> Web initialize/activate/deactivate/dispose lifecycle
```

Remove the old `Extension`/new `RegistryExtensionManager` split, PostgREST
binding store, target matcher, artifact-manifest fetch, and
`@inkcre/extension-runtime`. Preserve the working MF loading fixes, UI behavior,
failure compensation, and platform-specific lifecycle behind the single facade.

One management API replaces `/extensions/{legacy-id}` plus
`/extension-installations/{namespace}/{name}`. Exact routes and state-port
transport belong to HLD, but there is one semantic install/config/enable/disable/
uninstall model and one canonical Extension Name.

### 5. Recreate Registry Storage From The Native Schema

The public Registry is a demo and has no authoritative package, credential, or
artifact data to preserve. Recreate its D1 database/migration history and clear
its R2 bucket rather than carrying a transformation from the rejected model.
The new initial schema contains namespace/publisher authority, Extension
Name/Nickname, Release/lifecycle/provenance, Python project/release/files, and MF
Remote snapshot associations—no `targets` table.

Re-seed the reserved `inkcre` namespace and rotate its scoped publisher
credentials into the peer delivery environments. Do not expose raw values in
logs or task evidence even though the demo has no secret-bearing production
data.

The old Twitter `0.1.0`, blackbox package, target rows, generic manifests, and R2
blobs are deleted outright. New native Releases use the versions declared by
their source packages; no historical Registry version is reinterpreted or
migrated.

### 6. Simplify CI/CD By Following Native Boundaries

Do not weaken protected-main, exact-SHA, frozen dependency, or same-artifact
delivery controls. Remove checks whose only purpose was proving the rejected
architecture.

`ext-reg` checks become:

1. frozen Python environment plus the minimal Wrangler tool install;
2. format/lint/type/unit tests for service and publisher tooling;
3. Worker dry build;
4. one local black-box Python lane: prepare, native upload, Simple read,
   install/entry-point proof;
5. one local black-box MF lane: snapshot upload, public manifest/assets/CORS
   proof;
6. exact-main D1 migration, Worker deploy, and read-only production smoke.

Delete the pnpm workspace, TypeScript Runtime/API build, cross-language contract
generation, Python 3.12 Runtime client compatibility matrix, Web package release,
generic target fixtures, and production-write blackbox. Node/pnpm may remain only
as pinned Cloudflare Wrangler tooling, not as a second application stack.

Peer delivery becomes independent of application deployment:

- Core extension CD builds/tests a wheel and publishes it through native
  association plus `uv publish`; it never rebuilds or gates the Core application
  image and never writes an embedded catalog;
- Web CI builds each Remote once, uploads that checked artifact, and its delivery
  publishes the exact snapshot; Pages deploy consumes its own checked SPA
  artifact without rebuilding the Remote;
- a same-name/version upload with different bytes fails publication, making the
  native package version the release intent; identical retry is idempotent;
- first-party and third-party publication use the same Registry APIs.

Path filters may avoid unrelated publication runs, but correctness cannot depend
on a mutable “latest” artifact, controller checkout, manually duplicated digest,
or production-only test package.

### 7. Cutover And Rollback Sequence

```text
preflight and diagnostic snapshot
  -> publish all retained native Distributions
  -> verify Registry native reads anonymously
  -> enter maintenance / stop Extension mutations
  -> recreate Registry D1/R2 + deploy native API
  -> reset the three deployment Extension relations to one empty table
  -> deploy matching Core and Web Host SDKs
  -> regenerate/verify client DB contract
  -> production install/enable/disable/restart/uninstall journey
  -> leave maintenance
```

The rollback unit is the entire cutover: rebind the previous Registry resources,
restore the three Extension relations from the diagnostic snapshot, and redeploy
the previous exact Core and Web artifacts. Do not attempt field-by-field reverse
translation after the new demo has accepted mutations.

## Acceptance Boundary

Batch 04 remediation is complete only when:

- repository search finds no production `legacy extension`, target key/digest,
  generic matcher/manifest, binding table, embedded bundle, or shared Runtime/API
  package path;
- one canonical deployment relation starts empty, affects no unrelated table,
  and owns all subsequent version/config/schema/per-Peer enablement;
- every retained first-party Extension resolves from Registry-hosted native
  bytes, not an application image;
- Core and Web each have one Host facade and their original platform-specific
  lifecycle behavior remains tested;
- production catalog has no blackbox package, generic target Release, or old
  artifact bytes;
- native Python and MF publish/read/consume journeys pass with unauthorized,
  version mismatch, overwrite conflict, missing format, outage, and rollback
  evidence;
- exact-main governance remains, while rejected-architecture checks and packages
  are gone.

## Batch Review Boundary

This strategy is accepted. The remaining work is HLD, targeted PoC, local
implementation, verification, and an exact-object authorization handshake before
Git and public-demo delivery mutations.
