# Architecture

## Authority And Topology

The Registry owns the common Extension release control plane and hosts native
Distribution bytes:

```text
peer CI ── wheel + legacy upload ─┐
                                 ├─> Registry ─> D1 identity/lifecycle
peer CI ── MF ZIP snapshot ──────┘           └─> private R2 bytes

Core Host SDK ─> exact Release ─> Simple API ─> native Python installer
Web Host SDK  ─> exact Release ─> mf-manifest ─> native MF Host
```

Extension Name/Nickname, Release state, publisher scope, provenance, and typed
native association metadata are Registry authority. Wheel/Core Metadata,
`Requires-Python`, dependencies, tags, and entry points remain Python
authority. `mf-manifest.json` and its shared/exposed asset metadata remain
Module Federation authority. Deployment `installed`, Peer `enabled`, and
process/browser `running` are deliberately not Registry state.

There is no generic target, compatibility predicate, `artifact_format`,
cross-format manifest, capabilities digest, or deployment Distribution binding.

## Identity And Lifecycle

- Extension Name is canonical lowercase `namespace/name`; Nickname is the
  human-facing label.
- A Release is Extension Name plus strict SemVer without a leading `v` or build
  metadata.
- Stable Python Distribution versions are identical to the Release version.
  Only the explicitly lossless `a.N`, `b.N`, and `rc.N` pre-release mappings
  are accepted.
- One Release may have one Python Project association and one Module Federation
  snapshot association. Either association is optional.
- Source repository/revision/build provenance belongs to its typed native
  association. Python and Web may append independently from different peer
  repositories without imposing one false Release-level build identity.
- `preparing` is private. Publication requires at least one validated native
  Distribution. A previously missing format may be appended after publication.
- Existing association metadata, filenames, and bytes are immutable. Identical
  retries are idempotent; a same-slot conflict requires a new Release.
- `published ↔ yanked` preserves exact descriptor and bytes. Catalog selection
  excludes yanked Releases while Simple links carry the yank reason. Operator
  `blocked` is a separate read-denial state.

## Native Python Surface

`POST /legacy/` accepts the declared-length multipart protocol used by uv and
Twine. Namespace Basic-password or bearer credentials locate one prepared
Project/version association. Admission verifies the claimed SHA-256, wheel
filename, normalized Project, PEP 440 congruence, Core Metadata, and the exact
declared entry point. Archive paths, duplicates, symlinks, encryption,
decompression size, and compression ratio fail closed.

Anonymous consumers use Simple API 1.1 at `/simple/` and
`/simple/{normalized-project}/`. Both PEP 503 HTML and PEP 691 JSON are served
with exact media types and `Vary: Accept`. File links expose SHA-256,
`Requires-Python`, size, upload time, yank reason, and PEP 658 Core Metadata.
Immutable archives and `.metadata` sidecars are D1-gated beneath `/packages/`.

The MVP accepts wheels only. Its entire multipart request must include
`Content-Length` and fit within 20 MiB. The parser's in-memory spool threshold
is above that bound because Python Workers cannot use Starlette's thread-backed
temporary-file spill. Chunked requests receive `411`; larger requests receive
`413` before parsing.

## Native Module Federation Surface

An authenticated publisher posts one ZIP snapshot to
`/v1/extensions/{namespace}/{name}/releases/{version}/module-federation`.
Admission requires a root `mf-manifest.json`, a relative Remote entry, and every
referenced shared/exposed JS/CSS asset. All paths must be normalized,
traversal-free, non-duplicated, non-symlink members within bounded expansion.

The producer manifest must contain `metaData.publicPath: "./"`. Admission
materializes only that native field from the validated canonical
`PUBLIC_ORIGIN` binding as the absolute immutable Registry prefix;
it does not generate another public schema. D1-gated manifest/assets are served
beneath `/extensions/{namespace}/{name}/{version}/module-federation/` with CORS,
ETag, and one-year immutable caching.

## Persistence And Publication

D1 uses strict foreign-keyed tables for namespaces, hashed credentials,
Extensions, Releases, Python associations/files, and Module Federation
associations. Upload bytes first enter private immutable staging keys in R2.
Only after archive validation and R2 writes does D1 expose the association.
Publication is a conditional D1 state transition that proves at least one ready
association; guessed staging keys are never a public read authority.

D1 cannot roll back R2, so an interrupted admission may leave unreachable
staging objects for a bounded janitor/lifecycle rule. Public raw-byte routes
always prove a `published` or `yanked` D1 association before reading R2.

## Public API

The canonical public origin is `https://registry.inkcre.dev`. `GET /` serves a
small server-rendered, read-only catalog of published Extensions. It has no
independent state or client-side compatibility logic and reads the same
Registry projection as `GET /v1/extensions`.

The generated [`contracts/openapi.json`](contracts/openapi.json) is mechanical
truth. The stable control-plane routes are:

- `GET /v1/extensions`
- `GET /v1/extensions/{namespace}/{name}`
- `GET /v1/extensions/{namespace}/{name}/releases/{version}`
- `POST /v1/extensions/{namespace}/{name}/releases`
- `POST .../releases/{version}/publish`
- `POST .../releases/{version}/yank` and `POST .../unyank`
- `POST /legacy/`
- `POST .../releases/{version}/module-federation`

Mutable control/Simple responses use `no-store` so lifecycle changes are visible
without CDN cache-key or purge configuration. Native bytes use immutable
caching because same-version bytes are never replaced.

## Security Boundary

Raw credentials never enter D1; only SHA-256 token hashes are stored and scoped
to one active namespace. uv/Twine Basic authentication requires the conventional
`__token__` username; control-plane clients use Bearer. Public reads are anonymous only after D1 lifecycle
authorization. The Registry validates structure and integrity, not publisher
trust: Python code executes inside a trusted Core process and an MF Remote has
host-page privileges. Host SDK compatibility and native dependency/runtime
negotiation are checked by their platform consumer before executable bytes run.
