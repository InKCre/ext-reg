# High-level Technical Design

## Status

**Complete for MVP.** Product semantics come from
[`15-product-design.md`](15-product-design.md). This document selects the MVP
topology and contract boundaries. Exact code layout, SQL migrations, HTTP
payload schemas, and peer file changes belong to the implementation plan.

The two design-changing uncertainties were:

1. whether a Cloudflare Python Worker can run the selected thin FastAPI service
   with D1 and R2 bindings reproducibly; and
2. whether a Vite Module Federation remote built with a relative asset base can
   load all of its chunks from an immutable Registry artifact prefix.

Both PoCs passed; evidence is owned by
[`work/09-hld-pocs.md`](work/09-hld-pocs.md). The Python Worker topology and
relative Module Federation artifact prefix are therefore admitted. A future
failure may still use the documented thin TypeScript edge fallback without
changing the product or protocol.

## System Topology

```text
publisher repository / peer repository
  -> peer-owned build and tests
  -> Python publisher CLI
       -> authenticated blob upload ---------------------+
       -> authenticated target association/publish ------+-- Registry API
                                                             Python Worker
anonymous consumer / deployment adapter -----------------+     |
  <- package/version/target metadata                            +-- D1 metadata
  <- immutable target files                                    +-- private R2 blobs

shared deployment database
  -> one installation: namespace/name@exact-version
  -> zero or more peer bindings: peer -> target key + target digest

client-web adapter -> Registry-hosted Module Federation files -> browser runtime
core-py adapter    -> Registry metadata -> admitted bundle already in app image
```

The Registry has one public origin. Metadata and artifact reads are anonymous.
Publication is authenticated. D1 and R2 are never exposed as independent
product authorities.

## Selected Technology

### Service And Edge

- A single Cloudflare Python Worker runs a thin FastAPI application.
- Python 3.13 and Node 22 are the repository toolchain baselines; `uv` owns environments and
  the lock; FastAPI/Pydantic own HTTP and validation; Typer owns the publisher
  CLI; `httpx` owns its network client.
- The Worker performs validation, authorization, small-file hashing, D1
  coordination, and R2 reads/writes. It does not build Extensions or execute
  Extension code.
- Python Workers are currently a Pyodide/WASM open beta. The PoC proved FastAPI,
  D1, and R2 locally and on the production runtime. `pywrangler` currently fails
  under Node 26 because its Pyodide setup still passes a removed WASM flag, so
  Node 22 is pinned. A thin TypeScript Worker remains the bounded fallback;
  moving the whole service into a container is not the first fallback.

### Metadata And Artifact Storage

- D1 is the authoritative transactional metadata store. MVP uses the primary
  database only; read replicas and Sessions are unnecessary.
- Private R2 stores canonical target manifests and file blobs under SHA-256
  content addresses. R2 keys never carry mutable package meaning.
- Files are uploaded through the Worker. The Worker computes SHA-256 and rejects
  a claimed digest mismatch before writing. MVP limits each file to 20 MiB;
  large direct/multipart uploads are a later concern.
- Public immutable artifact routes return permissive CORS and long-lived
  immutable cache headers. Mutable package/version metadata uses short caching.
- GHCR/OCI is not the canonical Registry artifact backend. It remains suitable
  for the existing core application image, but using it for Web file bundles
  would add registry auth/media-type/index behavior without improving MVP
  semantics.

### Publisher Authentication

- A Registry operator manually provisions a namespace and one or more random
  namespace-scoped bearer credentials.
- D1 stores only each credential's SHA-256 hash, namespace, label, creation time,
  and disabled state. Raw credentials exist only in publisher secret stores.
- The same HTTP publication protocol is used by first-party and third-party
  publishers. `inkcre` differs only because its namespace is operator-reserved.
- GitHub OIDC trusted publishing, Cloudflare Access, account/team management,
  and self-service credential issuance are deferred. Static scoped credentials
  are the smallest revocable mechanism sufficient for the two peer CDs.

## Registry Data Model

The logical schema has five records. Exact SQL names may vary without changing
the model.

| Record | Identity | Mutable fields | Authority |
| --- | --- | --- | --- |
| Namespace | `namespace` | display owner, status | Registry operator |
| Credential | token hash | label, disabled | Registry operator |
| Extension | `namespace/name` | public display metadata | namespace publisher |
| Release | `namespace/name@version` | state until published; yank/block state | namespace publisher/operator |
| Target | release + `target_key` | none after acceptance | namespace publisher |

Target rows contain the canonical target-manifest digest, artifact format,
entry point, compatibility contract, source repository/revision, and timestamps.
The database enforces one release per coordinate/version and one immutable slot
per release/target key.

The first target upload creates a `preparing` release. Publication is one D1
transaction that verifies at least one accepted target and changes the release
to `published`. A published release accepts only previously unused target keys.
Retrying the same key and digest is idempotent; a different digest conflicts.

`yanked` remains readable by exact metadata lookup but is excluded from new
selection. `blocked` denies new target-file reads. Ordinary APIs never delete a
published release or its content-addressed blobs.

## Target Artifact Contract

### Canonical Target Manifest

Every target is represented by one language-neutral canonical JSON document.
Its SHA-256 is the **target digest** bound by deployments. It contains:

- contract version;
- artifact format and relative entry point;
- the Target Compatibility Contract;
- an ordered map of safe relative file paths to SHA-256, byte size, and media
  type; and
- no mutable or non-executable provenance fields.

Canonical serialization is deterministic and owned by `ext-reg`. Paths must be
relative, normalized, unique, and traversal-free. The manifest may describe one
archive file or a multi-file Web bundle. Each listed file is separately stored
by its content digest in R2.

Source repository, source revision, workflow/run identity, and publisher are
stored on the immutable target association outside the target digest. This lets
an unchanged artifact retry idempotently from a later application build while
preserving the first accepted provenance; non-executable metadata cannot change
executable identity.

The immutable public prefix is conceptually:

```text
/v1/artifacts/{target-digest}/manifest
/v1/artifacts/{target-digest}/files/{relative-path}
```

The file endpoint resolves the path through the already-hashed manifest and then
reads the referenced content-addressed blob. Clients never follow mutable tags.

### Compatibility Contract

A target manifest contains one conjunction of conditions:

```text
condition = vocabulary-key + operator + expected-value
operator  = equals | semver
```

- `equals` compares controlled opaque values.
- `semver` asks whether the consumer's exact SemVer capability satisfies the
  producer's range.
- Every condition is mandatory. Unknown keys, missing consumer values, invalid
  values, or unsupported operators fail compatibility.
- There is no Boolean expression language, optional condition, or target
  priority in MVP.

The vocabulary is versioned with the Runtime/API contract. Initial dimensions
cover only facts required by the two acceptance adapters:

- accepted integration format (`module-federation-esm` or `python-bundle`);
- InKCre Extension lifecycle API version;
- Module Federation runtime and share scope;
- versions of shared Vue and `@inkcre/core` contracts;
- ECMAScript execution baseline when emitted code requires it; and
- Python interpreter version.

`client-web`, `core-py`, browser brands, repository names, and target labels are
display information, not compatibility inputs. A peer adapter constructs its
Platform Profile from its actual build/runtime contract, filters targets, then
uses its own deterministic preference and stable target-key tie-break. It binds
the selected target key and target digest before declaring enablement.

## Public And Publisher API Boundary

The versioned HTTP API exposes these resource families; exact path spelling and
payloads are fixed in the implementation contract after the PoCs.

### Anonymous read

- list/search published Extensions;
- get one Extension and its versions;
- get one exact release and all public target declarations;
- get a target manifest by digest; and
- get a target file by digest and safe relative path.

### Scoped publication

- upload one content-addressed blob with a claimed SHA-256;
- associate one canonical target manifest with a target key;
- explicitly publish a preparing release; and
- yank a published release.

Blob upload is idempotent by digest. Target association is committed only after
all referenced blobs exist and the canonical manifest digest has been verified.
No endpoint accepts a target archive and implicitly guesses metadata.

The repository publishes language-neutral JSON Schemas and OpenAPI as generated
contract artifacts. A Python CLI is the reference producer. Peer adapters may be
native Python or TypeScript, but must pass the same small conformance fixtures.

## Deployment Installation Model

The existing shared `extensions` row conflates artifact-local catalog data with
installation and cannot hold namespace or per-peer digest bindings. MVP adds a
clean deployment-owned model rather than overloading that row:

```text
extension_installation
  namespace, name, exact version, shared config/config schema
  primary key(namespace, name)

extension_peer_binding
  namespace, name, peer UUID, target key, target digest
  primary key(namespace, name, peer UUID)
  foreign key -> installation
```

- Installation existence means installed and starts with no bindings.
- Binding existence means enabled for that peer and records the exact admitted
  target. `running` remains process/browser memory state.
- Install validates that the exact release is published, then inserts only the
  installation record.
- An adapter resolves and admits a target, starts it, then persists its binding.
  Any failure cleans up transient runtime effects and leaves the peer disabled.
- Disable stops runtime effects before deleting only that peer's binding.
- Uninstall is one transaction that requires no bindings, then removes shared
  configuration and the installation.

`core-py` owns the database migration and deployment-level install/uninstall
coordination. Peer-local adapters own enable/disable because only the peer can
admit and operate its runtime. The ext-reg Runtime/API contract specifies these
state transitions and request/response/error semantics; peer repositories only
implement host-specific loading hooks.

The legacy `extensions` table remains migration input until its existing data
has been deliberately handled. Startup scanning must no longer recreate deleted
Registry installations. Exact migration and compatibility behavior is fixed in
the cross-repository implementation plan.

## Peer Admission And Runtime Paths

### `client-web`

1. Build the existing first-party Extension as a Module Federation ESM remote
   with a relative asset base.
2. Peer CD publishes the complete output file set and target manifest.
3. The browser adapter reads the installed release, builds its Platform Profile,
   resolves a compatible target, and binds its exact digest.
4. It loads the remote entry from the immutable artifact prefix, calls the
   Extension lifecycle hooks, and only then persists the peer binding.
5. Disable calls deactivate/dispose, unregisters the remote where supported, and
   removes the binding.

The Registry serves coherent remote entry and chunks from one target manifest.
The remote executes with host-page privilege; the contract makes no isolation
claim.

### `core-py`

1. Peer CD creates a deterministic Python target bundle, publishes it, and also
   embeds that exact bundle plus target manifest in the core application image.
2. At enable, the adapter may read Registry metadata but accepts a target only
   when its target digest exists in the image's admitted-bundle catalog.
3. It extracts/imports the embedded bundle, instantiates the Runtime/API hooks,
   starts them, and persists the binding.
4. Disable closes hooks and removes the binding; uninstall removes only database
   state, not inert bytes in the immutable application image.

No Registry response can cause arbitrary live-downloaded Python to execute.
Artifact presence is not installation: the current startup `sync()` behavior
must stop turning every embedded bundle into an installed database row.

## Failure And Consistency Semantics

- D1 publication transactions prevent a target association or state change from
  becoming partially visible. R2 orphan blobs are harmless content-addressed
  data and may be collected after MVP.
- Concurrent identical uploads converge; a target-key digest conflict returns a
  conflict without mutation.
- Registry unavailability or missing/mismatched bytes fails publish, install,
  enable, or cold load without changing durable deployment state.
- A running peer is not stopped because the Registry becomes unavailable.
- Peer enable is compensating rather than globally transactional: failed loading
  removes transient hooks and does not create a binding.
- Disable that unloads successfully but cannot delete its binding leaves a
  durable enabled/not-running state that startup can retry; running is never
  inferred solely from HTTP success.
- Published target append never changes an existing binding. Re-resolution is
  explicit and outside the MVP lifecycle journey.

## Production And Operational Boundary

- One Worker production deployment, one D1 production database, and one private
  R2 production bucket are sufficient.
- Secrets are the Worker secret/config and two peer repository publisher tokens.
  No production database or R2 credential is exposed to publishers or browsers.
- Registry delivery follows protected-main exact-revision deployment. Peer target
  publication follows each peer's existing protected-main artifact/CD authority.
- Minimum observability is structured request/error logging plus release target,
  source revision, and digest audit fields. Dashboards, SLO machinery, mirrors,
  malware scanning, and advanced abuse/rate systems are deferred.
- Rollback deploys an earlier Worker revision without rewriting Registry release
  records. D1 migration changes must be forward-compatible and backed up before
  production application.

## HLD Exit

Both named risks passed their smallest experiments. HLD is complete. The next
gate is a cross-repository implementation plan mapping this design to exact
files, migrations, workflows, secrets, deployment order, rollback, and
black-box verification in all three repositories.
