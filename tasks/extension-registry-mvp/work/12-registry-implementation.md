# Registry Implementation

## Status

**Current.** The local Registry vertical slice and executable project foundation
are complete. Repository delivery and production deployment are next.

## Implemented Surface

- Python 3.13 `uv` project with the Registry contract package, HTTP client,
  deterministic publisher CLI, FastAPI control/read plane, D1 repository, and
  Cloudflare Worker entry.
- D1 migration for namespaces, hashed scoped credentials, packages, releases,
  and append-only targets.
- Private R2 content-addressed blobs plus immutable public manifest/file routes.
- Canonical generated JSON schemas, Registry OpenAPI, and contract revision.
- `@inkcre/extension-runtime` with browser Registry client, controlled
  compatibility matcher, deterministic selection, lifecycle controller, and
  focused tests/build.
- One root `pnpm check` that validates generated contracts, Python and Web
  formatting/lint/types/tests/builds, and a real Pyodide Worker dry-run.

## Corrections Found By Execution

1. The legal controlled condition key `shared.@inkcre/core` cannot be filtered
   by a generic punctuation grammar before controlled-vocabulary validation.
2. A canonical manifest digest may be reused by multiple target associations;
   D1 therefore indexes but does not globally unique-constrain it. Artifact
   lookup prefers a published association so blocking one release does not
   accidentally block identical bytes used by another valid release.
3. Current Cloudflare Python Workers select Pyodide 0.28.3/CPython 3.13. The
   initial Python 3.12/Pydantic 2.13 assumptions failed the real Worker compile.
   The Registry now uses Python 3.13 and the available Pydantic 2.10.6 WASM
   wheel; `core-py` independently remains Python 3.12.
4. Wrangler executes its Python entry as a top-level module. A `src/worker.py`
   shim preserves the `inkcre_extension_registry` package context and valid
   relative imports.
5. CLI-only HTTP/Typer dependencies were moved to an optional extra/dev group.
   The production Worker bundle fell from roughly 15 MiB uncompressed to 8.25
   MiB (2.12 MiB gzip).
6. The Worker compatibility date is pinned to the newest date supported by the
   checked-in Wrangler/workerd release, not the local calendar date.

## Verification Evidence

The following passed on 2026-08-10:

```text
pnpm check
  generated contracts: current
  Ruff format/lint: pass
  Pyright: 0 errors
  Pytest: 10 passed
  Prettier/ESLint/TypeScript: pass
  Vitest: 2 files / 2 tests passed
  Python sdist+wheel: built
  Web runtime package: built
  pywrangler deploy --dry-run: pass, 8.25 MiB / 2.12 MiB gzip
```

The real local Worker path also passed:

```text
wrangler d1 migrations apply DB --local
wrangler d1 execute DB --local --file tests/fixtures/local-seed.sql
pywrangler dev --port 8791
inkcre-ext publish-target ...
GET exact release -> published
GET immutable manifest -> 200
GET cross-origin artifact file -> 200
declared file SHA-256 == downloaded file SHA-256
```

Observed local target identity:

```text
inkcre/blackbox@0.1.0
web.chrome-vue-mf
sha256:3d51fd949dacea5fcc9907328024eaeaf480b9d4ffd2b979857fb799d6a00f2a
```

Local Wrangler state and fixture data are ignored and are not production data.

## Remaining Slice

- Add repository CI, exact-main release, and exact-main production delivery.
- Add concise repository architecture/filesystem/contribution/operations docs.
- Create the public remote, push coherent commits, and prove CI.
- Provision production D1/R2, seed raw tokens only into peer GitHub secrets,
  deploy the Worker, and repeat the public black box before peer integration.
