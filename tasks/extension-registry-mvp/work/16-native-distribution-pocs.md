# Native Distribution HLD PoCs

## Status

Three architecture-changing risks are now proved locally:

1. all six Core first-party Extensions can be normal wheels in one PEP 420
   namespace and can be selected from a standards-shaped Simple index;
2. the current Vite producer and MF Host can use a native manifest across
   origins, provided the Registry materializes an absolute immutable
   `metaData.publicPath`; and
3. a Cloudflare Python Worker can accept uv-compatible multipart uploads up to
   the 20 MiB MVP cap, provided Starlette never spills to a thread-backed file
   and chunked uploads are rejected.

No Git, public Registry, Cloudflare, or deployment-database mutation occurred.
All runtime/server experiments used disposable worktrees and local resources.

## PoC 01 — Six Native Python Wheels

### Procedure

[`../poc/native_wheels.py`](../poc/native_wheels.py) performed the following
against `core-py` `origin/main` `596510b` with Python `3.12.10`:

1. archived the six source directories from the exact Git revision;
2. built six temporary setuptools wheels with no `extensions/__init__.py`;
3. declared `inkcre.core.extensions` entry points;
4. served a local PEP 503-shaped index with SHA-256 links and
   `data-requires-python`;
5. used `python -m pip download --only-binary=:all:` for every exact Project
   version;
6. installed the wheel files into a temporary site directory;
7. loaded every entry point against the matching Core source revision; and
8. initialized Source and Resolver contributions and inspected their identities.

Command:

```text
PYTHONPATH=<ext-reg-src>:<temporary-contract-deps> \
python3 tasks/extension-registry-mvp/poc/native_wheels.py \
  --core-repo <detached-core-origin-main> \
  --core-python <core-python-3.12>
```

### Result

- Six wheels built and were selected from the local Simple API:
  `inkcre-ext-github`, `inkcre-ext-learn_english`, `inkcre-ext-mail`,
  `inkcre-ext-rss`, `inkcre-ext-telegram`, and `inkcre-ext-twitter`, all
  `0.1.0`.
- Every wheel exposed `extensions.<id>:Extension` in
  `inkcre.core.extensions`.
- No wheel contained `extensions/__init__.py`; all six contributed to the same
  PEP 420 namespace.
- Every loaded class originated inside the wheel install directory rather than
  the checked-in Core source tree.
- Seven existing Source type strings were preserved exactly, including
  `extensions.twitter.bookmark.Source` and
  `extensions.telegram.source.Source`.
- Nine existing Resolver type strings were preserved exactly.
- There were no initialization errors against the matching Host SDK revision.

An intentional mismatch run loaded the same wheels against a divergent local
Core branch and failed during contribution imports. That result is expected and
confirms why the producer-declared Host SDK range plus per-Host conformance test
is required; co-location alone had hidden no magical compatibility guarantee.

### Decision

Use normal wheels with PEP 420 packages `extensions.<id>` and standard entry
points. Do not rename Python modules or migrate persisted Source/Resolver
identities during this cutover. Each wheel's release gate must load its entry
point and initialize contributions against every declared compatible Core Host
SDK line, not merely build the archive.

## PoC 02 — Native Module Federation Manifest

### Procedure

Against `client-web` `origin/main` `4c391f6`:

1. enabled `manifest: true` in the temporary Twitter federation build;
2. built `@inkcre/core`, then `@inkcre/ext-twitter`, using
   `@module-federation/vite 1.7.1`;
3. parsed `mf-manifest.json` and verified its Remote entry plus every referenced
   shared/exposed asset was relative and present;
4. served the Remote from `127.0.0.1:4189` with CORS and the Host page from
   `127.0.0.1:4190` using `@module-federation/enhanced 0.22.1`; and
5. loaded `extension.twitter` in Chromium through the native manifest URL.

### Result

- Vite emitted `mf-manifest.json`, `remoteEntry.js`, and a closed referenced
  asset set with `metaData.publicPath: "./"`.
- The raw manifest failed cross-origin: the Host attempted
  `http://127.0.0.1:4190/.../remoteEntry.js`, resolving the relative public path
  against the Host origin.
- With only `metaData.publicPath` materialized as the absolute immutable Remote
  prefix, the same browser loaded the manifest, Remote entry, JS, and CSS from
  the Registry origin with no failed request.
- The loaded default export contained Web's existing `initialize`, `activate`,
  `deactivate`, and `dispose` hooks.

### Decision

The Registry hosts a native MF manifest but normalizes its native
`metaData.publicPath` field at admission/publication. This is not a generic
InKCre artifact manifest. The producer retains `base: './'`; the Registry
validates the relative closure, assigns the immutable public prefix, and serves
the resulting native manifest.

## PoC 03 — Python Worker Multipart Boundary

### Procedure

A disposable `ext-reg` worktree added `python-multipart 0.0.32` and one local
FastAPI endpoint, then ran the actual Python Worker/ASGI stack under Wrangler
with pinned Node `22.22.3`. Requests used real multipart `content`, `:action`,
and `protocol_version` fields.

The experiment exercised:

- declared 1 MiB, 20 MiB, and 21 MiB requests;
- chunked 1 MiB and 21 MiB requests; and
- a real `uv publish` of the existing 28.1 KiB Registry wheel.

### Result

- Node 26 reproduced the known Pyodide WASM-flag failure; Node 22 started the
  Worker successfully.
- `python-multipart` is supported by the Worker packaging/runtime.
- Starlette's default 1 MiB spooling failed for a 20 MiB file with
  `RuntimeError: can't start new thread`; Python Workers cannot use that
  thread-backed spill path.
- Setting the parser's spool threshold above the bounded file cap kept uploads
  in memory: declared 1 MiB and 20 MiB returned `200` with exact SHA-256;
  declared 21 MiB returned `413` before parsing.
- An oversized chunked request reaches the spill path before endpoint code can
  reject it. Requiring `Content-Length` made all chunked requests return `411`
  before parsing.
- `uv publish` sent a declared-length multipart request and completed
  successfully against the PoC endpoint.

### Decision

MVP upload endpoints require `Content-Length`, cap the entire request/file at
20 MiB, keep the bounded multipart file in memory, and reject chunked uploads.
This is adequate for the six wheels and current MF Remote and materially simpler
than a second streaming edge service. Large/chunked upload support must use a
future native Worker/R2 multipart seam rather than silently enabling Starlette
spooling.

## Remaining Proof Before Delivery

These are implementation/rehearsal gates, not unresolved product design:

- safely inspect hostile wheel/MF archives and verify native metadata;
- prove dependency-plan conflict handling and restart-required Python upgrades;
- prove D1/R2 staging, idempotency, rollback, yanking, cache negotiation, and
  read-after-write in the new Registry implementation;
- rehearse the exact three-relation PostgreSQL hard cut with unrelated-data
  preservation; and
- run the complete native publish/install/enable/disable/uninstall journey
  locally before requesting Git and public-demo delivery authorization.
