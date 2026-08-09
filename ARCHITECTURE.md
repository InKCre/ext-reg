# Architecture

## Purpose And Authority

The InKCre Extension Registry is a public, multi-publisher package host. It owns
canonical Extension coordinates, immutable versions and target associations,
publisher admission, public discovery, and digest-addressed artifact delivery.

It does not own a deployment's installation, a peer's enablement, or volatile
runtime state:

```text
Registry:   namespace/name@version -> target manifests and immutable bytes
Deployment: one exact installed version -> per-peer target/digest bindings
Peer:       disabled or enabled for its own binding
Runtime:    stopped or running lifecycle side effects
```

First-party extensions remain in peer repositories. Their CD uses the same
reserved-namespace publication protocol as any other publisher.

## Production Topology

```text
publisher CD
  -> authenticated Registry API
  -> canonical target manifest
  -> D1 release/target association
  -> private R2 content-addressed blobs

anonymous consumer
  -> public Registry metadata
  -> adapter-owned compatibility selection
  -> exact target digest
  -> immutable public manifest/files
```

One Cloudflare Python Worker exposes the FastAPI metadata/publication surface
and a small direct artifact-file path. D1 is semantic metadata authority. R2 is
only byte authority. A manifest digest commits to artifact format, entrypoint,
mandatory compatibility conditions, file paths, sizes, media types, and file
SHA-256 values. Source repository/revision/build provenance belongs to the
target association and deliberately does not alter the content digest.

## Identity And Publication

- Coordinate: canonical lowercase `namespace/name`.
- Version: strict SemVer without `v` or build metadata; published content is
  immutable.
- Target key: stable association slot/display coordinate, not compatibility.
- Target digest: SHA-256 of canonical target-manifest JSON.
- File blob: global SHA-256-addressed bytes.

A publisher uploads blobs, associates one new immutable target key with a
version, and explicitly publishes after at least one target exists. Published
versions may append new target keys because target completeness is deployment
relative. Repeating the same key/digest is idempotent; changing the digest of an
existing key conflicts. Yanking prevents new selection without mutating remote
deployment state. Operator blocking denies artifact delivery but preserves
metadata and audit evidence.

## Compatibility And Runtime/API

Each target states a conjunction of mandatory requirements over a consumer
adapter's Platform Profile. Controlled keys currently cover integration format,
Extension lifecycle API, Module Federation runtime/share scope/shared packages,
ECMAScript, and Python. Operators are exact equality and SemVer range. Missing
or unknown mandatory facts fail closed.

The Registry validates and indexes declarations; an extension runtime adapter
owns profile construction, matching, deterministic preference, and exact
target/digest binding. `client-web` may load a bound, privileged
Module-Federation remote from the Registry. `core-py` must instead admit a
Python target into its trusted build/deployment artifact before enablement; it
never executes arbitrary live-downloaded Python.

The language-neutral executable contract is generated under `contracts/`.
Python owns canonical serialization and service models. The
`@inkcre/extension-runtime` package owns the browser Registry client,
compatibility matcher, lifecycle executor, and `ExtensionModule` interface.

## Public API

The generated [`contracts/openapi.json`](contracts/openapi.json) is mechanical
truth. Key routes are:

- `GET /v1/extensions`
- `GET /v1/extensions/{namespace}/{name}`
- `GET /v1/extensions/{namespace}/{name}/versions/{version}`
- `PUT /v1/blobs/{sha256}` (publisher)
- `PUT /v1/extensions/{namespace}/{name}/versions/{version}/targets/{target_key}` (publisher)
- `POST .../publish` and `POST .../yank` (publisher)
- `GET /v1/artifacts/{target_digest}/manifest`
- `GET /v1/artifacts/{target_digest}/files/{relative_path}`

Metadata may change as new targets are appended and is not immutable-cached.
Target manifests and files are digest-addressed with one-year immutable cache
headers. Artifact files allow cross-origin reads for browser remotes.

## Security Boundary

Public reads are anonymous. Publication uses namespace-scoped bearer credentials
whose SHA-256 values, never raw tokens, are stored in D1. MVP onboarding and
credential rotation are operator-controlled. Blob uploads are bounded to 20 MiB
per file and verified against the requested digest. Paths are normalized POSIX
relative paths and traversal is rejected.

The Registry does not claim sandboxing, malware prevention, provenance
attestation, or trustless execution. A web remote executes with host-page
privileges; Python targets execute in a trusted server process after deployment
admission. These facts are part of the consumer trust decision.
