# Peer Integration

## Status

**Complete.** Runtime/API `0.1.3` and both peer integrations are released. The
browser-native fetch receiver defect found by the first production Chromium run
is fixed in both the public Web Runtime/API and the Host adapter. The complete
production lifecycle journey passed with zero residue.

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

## Browser Fetch Receiver Correction

The production browser reached the public Registry install and Web-target enable
paths but Chromium rejected both native fetch calls with `Illegal invocation`.
The cause was observable JavaScript method binding, not CORS or Registry state:
the Web `RegistryClient` stored `globalThis.fetch` and later called it as a private
member, rebinding the native function's receiver to the client instance. The Host
adapter independently repeated the same pattern for artifact-manifest reads.

Runtime/API `0.1.3` therefore binds the selected fetch implementation to
`globalThis` at construction and adds a regression test whose default fetch stub
enforces that browser receiver. The already-deployed Host correction applies the
same rule at its adapter boundary. This is a Web Runtime/API implementation fix;
Registry endpoints, target identity, compatibility semantics, and Extension
Version remain unchanged.

## Execution Order

1. [complete] Release Runtime/API `0.1.2` through Registry protected-main checks.
2. [complete] Add and deploy Core's shared installation/binding schema, adapter,
   admitted target, and publication CD.
3. [complete] Regenerate the exact Web database contract, integrate the resolver,
   lifecycle, UI, Twitter target, and release-intent-aware CD.
4. [complete] Release Runtime/API `0.1.3`, update client-web's immutable
   Runtime/API tarball, and rerun the full production journey.

## Production Acceptance

- Registry PR [#3](https://github.com/InKCre/ext-reg/pull/3) merged as
  `55b52eed130c07062c77c9cdc2dd2cbd0aed08af`; release run `31340825004`
  published Runtime/API `0.1.3` and its immutable Web tarball.
- Client PR [#61](https://github.com/InKCre/client-web/pull/61) merged as
  `f29c98983a6fb29a5bb46e7b5cf3d4cd7ed1beb9`; exact-main checks
  `31341300838` and Pages delivery `31341424369` passed. The delivery correctly
  skipped Twitter target publication because that Host-only revision carried no release intent.
- Client acceptance-record PR [#62](https://github.com/InKCre/client-web/pull/62) later merged as
  docs-only main `4c391f64d8e416026272588a25cce955eaf8129f`; checks `31342369939` and
  Pages delivery `31342493450` passed while leaving runtime identity and target publication intact.
- Starting from zero rows/routes, the production UI installed one shared
  `inkcre/twitter@0.1.0` record with no bindings. Web enable selected
  `web-module-federation-v1@sha256:1cfb7744dcb97cecfe427b39f79994a3809f02a88be7ad67e2ef42f92d0a8220`;
  reload cold-restored the same digest. Core enable selected
  `python-core-v1@sha256:70d12049bd31c27e8bf024d26f9df91761a44fe4b58a7110681b171c50d1d679`
  and published three dynamic routes.
- Core disable removed its binding and routes. Web disable completed Module Federation lifecycle
  cleanup and removed its binding. UI uninstall then left zero installations, zero bindings, and
  zero Core Twitter routes after 22 successful Registry responses.
- Chromium reports the successful cross-origin 204 uninstall as
  `requestfailed(net::ERR_ABORTED)` after delivering the 204 response. A separate probe verified
  correct CORS, resolved UI await, authoritative 404 afterward, and zero residue. Acceptance
  excludes only that exact post-response observation and rejects all other browser failures.
