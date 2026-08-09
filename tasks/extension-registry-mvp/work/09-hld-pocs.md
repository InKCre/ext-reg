# HLD Targeted PoCs

## Status

**Complete.** Both named HLD uncertainties passed. These experiments selected no
new product behavior; they admitted the smallest implementation topology already
described in [`../30-architecture.md`](../30-architecture.md).

## PoC 1 — Cloudflare Python Worker, FastAPI, D1, And R2

### Question

Can the exact Python-first edge stack accept an HTTP body, hash it, coordinate
metadata in D1, store/read bytes in R2, and run on the real Cloudflare runtime?

### Method

- Based the temporary project on Cloudflare's official Python Worker FastAPI and
  D1 examples.
- Used `uv 0.12.3`, `workers-py 1.16.2`, `workers-runtime-sdk 1.6.8`,
  `fastapi 0.141.1`, and Wrangler/pywrangler 4.120.0-era tooling.
- POSTed one byte string; the Worker computed SHA-256, wrote it to an R2 binding,
  upserted digest/size through a D1 prepared statement, read R2 metadata, and
  returned both values.
- Repeated the request against a temporary real Worker, D1 database, and R2
  bucket in the Cloudflare account, then fetched the stored bytes through the
  Worker.

### Result

- Local and remote requests returned matching D1 size, R2 size, SHA-256, and
  original bytes.
- Remote test digest:
  `ab08f71a6cbfe42025efe44d226e4757c8411f4ce7c3480f40d51d92b2330a06`.
- Python Worker startup accepted the complete dependency graph and both real
  bindings.
- Node 26 failed during Pyodide environment creation because the tool passed
  `--experimental-wasm-stack-switching`; Node 22.22.3 passed. The project must
  pin Node 22 for pywrangler.
- The temporary Worker, D1 database, R2 test object, and R2 bucket were deleted
  after verification. They contained no user or production data.

### Decision

Admit Python Worker + FastAPI + D1 + R2. Keep a thin TypeScript Worker as the
bounded future fallback for beta-runtime regression, not as current complexity.

## PoC 2 — Module Federation Relative Artifact Prefix

### Question

Can the existing `client-web` Twitter remote use a relative Vite base and load
its entry plus all referenced chunks from a digest-shaped Registry prefix on a
different origin?

### Method

- Created a temporary detached worktree at `client-web` `origin/main`
  `37546a5`; the user's worktree was untouched.
- Changed only the temporary Twitter Vite `base` from
  `/twitter/client-web/` to `./`, then built `@inkcre/core` and
  `@inkcre/ext-twitter` with Node 22.22.3 and pnpm 11.11.0.
- Served the output with CORS and immutable cache headers under
  `/v1/artifacts/poc-digest/files/` from one origin.
- From a second origin, a headless Chromium page imported `remoteEntry.js`,
  initialized the container, loaded expose `.`, and called initialize, activate,
  deactivate, and dispose.

### Result

- Browser status was `passed`; there were no failed requests.
- The browser fetched `remoteEntry.js`, every dynamically imported JS chunk,
  and referenced CSS under the same artifact prefix.
- Lifecycle logs proved the exposed module was executed, not merely downloaded.
- Module Federation warned that the current remote advertises
  `@inkcre/core` 0.1.0 while requiring 0.0.0. The Registry design is unaffected,
  but peer implementation must replace this implicit inconsistency with a
  coherent Platform Profile and target condition.
- The temporary worktree was removed after verification.

### Decision

Admit relative-base multi-file Web targets and the digest-addressed artifact
prefix. No target-specific build-time Registry URL is required.

## Implementation Preflight — Worker Python Dependency Compatibility

The first full-project `pywrangler dev` preflight on 2026-08-10 selected
Pyodide 0.28.3 and CPython 3.13 from the Worker compatibility date. It correctly
rejected the initial Registry Python 3.12 bound and Pydantic 2.13 because that
Pydantic Core wheel was not present for the Pyodide runtime. Cloudflare's
current Python package guide likewise specifies Python 3.13; the Pyodide package
index exposes Pydantic 2.10.6 and Pydantic Core 2.27.2 for its CPython 3.13 WASM
target.

The Registry foundation therefore moved to Python 3.13 and bounded Pydantic to
2.10.6. This does not change the independent `core-py` target profile, which
remains Python 3.12. CPython-only dependency resolution is insufficient evidence
for a Python Worker release; the Worker-runtime compile stays a required check.

## Official References

- [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [Cloudflare Python packages](https://developers.cloudflare.com/workers/languages/python/packages/)
- [Cloudflare Python Worker examples](https://developers.cloudflare.com/workers/languages/python/examples/)
- [Cloudflare D1 Worker API](https://developers.cloudflare.com/d1/worker-api/d1-database/)
- [Cloudflare R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
