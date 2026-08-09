# Peer Integration

## Status

**Current.** Fresh peer worktrees exist. Runtime/API `0.1.1` is released and
proved Python 3.12 support; core integration then exposed a second packaging-only
consumer compatibility correction that is being released as `0.1.2`.

## Fresh Baselines

- Existing user worktrees remain untouched.
- Core worktree:
  `/Volumes/WorkSSD/Development/InKCre/.worktrees/core-py-extension-registry-mvp`,
  branch `feat/extension-registry-mvp`, based on fetched
  `origin/main@531b0d2`.
- Web worktree:
  `/Volumes/WorkSSD/Development/InKCre/.worktrees/client-web-extension-registry-mvp`,
  branch `feat/extension-registry-mvp`, based on fetched
  `origin/main@37546a5`.
- Both peers adopt SVC 10.0.1 while the installed CLI is 11.0.1. This task does
  not silently adopt or rewrite their SVC surfaces.

## Runtime/API Compatibility Correction

The released Python wheel `0.1.0` declared `Requires-Python >=3.13,<3.14`
because the Registry Worker must build on Cloudflare's CPython 3.13/Pyodide
runtime. That is the service build interpreter, not the public Runtime/API
client contract. Core-py production is Python 3.12, so consuming the wheel would
correctly fail before any adapter code runs.

The package source uses no Python 3.13-only syntax or API. Runtime/API `0.1.1`
therefore:

- declares Python `>=3.12,<3.14`;
- keeps `.python-version`, pywrangler, and the Worker delivery environment on
  Python 3.13;
- keeps Python and Web Runtime/API package versions coherent at `0.1.1`;
- derives FastAPI/OpenAPI service version from the package `__version__`;
- declares HTTP client dependencies behind the `client` extra so consumers can
  install the stable Registry client without inflating the Worker bundle;
- installs the built wheel with the `client` extra into a real Python 3.12
  environment and constructs the Registry client in the required Registry CI
  job.

This is a package compatibility fix, not a change to Extension Version,
Registry API semantics, or the lifecycle contract revision.

## Consumer Dependency Compatibility Correction

Core-py pins FastAPI `0.139.2` and Pydantic `2.11.9`. Runtime/API `0.1.1`
incorrectly required FastAPI `>=0.141,<0.142` and Pydantic `<2.11`, even though
the client and contract surfaces do not depend on those narrow Worker choices.
Forcing a peer framework upgrade would invert ownership: the public Runtime/API
must express its real compatibility instead of exporting the Registry service's
lock.

Runtime/API `0.1.2` therefore:

- supports FastAPI `>=0.139.2,<0.142` and Pydantic `>=2.10.6,<3`;
- keeps the deployed Worker's verified Pydantic `2.10.6` through a repository
  lock constraint, without placing that constraint in wheel metadata;
- installs the built wheel with its `client` extra on Python 3.12 after pinning
  the exact core-py FastAPI/Pydantic versions, and asserts neither is replaced;
- attaches the packed Web Runtime/API tarball to the public GitHub Release in
  addition to publishing GitHub Packages, so public consumers have an immutable
  anonymous distribution path;
- uses the workspace-root `dist/` as the pack destination; the previous
  `../../dist` argument escaped the checkout when pnpm executed the filtered
  command from the workspace root and therefore did not upload Web package
  evidence;
- keeps Python and Web Runtime/API versions coherent at `0.1.2`.

This is also package metadata only. Registry endpoints, contract revision,
Extension Version semantics, and target matching remain unchanged.

## Execution Order

1. Merge/release Runtime/API `0.1.2` through Registry protected-main checks.
2. Core-py: create its local task control surface and Impact Handshake; add the
   shared deployment installation/binding schema, adapter, admitted target, and
   publication CD; merge and deploy.
3. Client-web: regenerate the exact core database contract, consume Web Runtime
   `0.1.1`, integrate the target resolver/lifecycle/UI, publish Twitter, merge,
   and deploy.
4. Run the production install/enable/run/disable/uninstall journey against the
   shared database and record exact source, target, binding, and runtime effects.
