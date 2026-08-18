# Extension Units and Developer Toolkit Packaging

## Correction

The first preview-facade implementation put `inkcre-ext preview build` inside
the `inkcre-extension-registry` Python distribution. That is the wrong release
unit even though the source currently lives in the `ext-reg` repository.
Repository ownership and deployable/package ownership are not the same thing.

Three product units have different actors and lifecycles:

| Unit | Runs when | Primary actor | Owns |
| --- | --- | --- | --- |
| Extension Registry | Service runtime | Registry operator | HTTP API, auth, Release lifecycle, catalog, D1/R2 and public reads |
| Extension Host SDK | Peer runtime | Peer/Extension runtime | Native consumer, load/run/close and Peer-specific Extension API |
| Extension Developer Toolkit | Development and CD | Extension developer/publisher | Producer metadata, native artifact inspection, preview assembly and publishing commands |

`inkcre-ext preview build` belongs to the **Extension Developer Toolkit**. It
does not belong to the Registry service or either Host SDK.

## Dependency Direction

The accepted dependency topology is:

```text
Extension source
  -> Extension Developer Toolkit
  -> build / inspect / preview / publish
  -> Extension Registry

Extension Host SDK
  -> Registry public protocol
  -> native consumer (pip / Module Federation Host)
  -> Extension runtime
```

The Registry service may depend on the Toolkit's pure Python library for native
artifact inspection and static/public projection functions. That is a normal
one-way library dependency and prevents the service and Toolkit from copying
wheel, MF manifest or Simple-index rules. The Toolkit must not depend on the
Registry service implementation. Host SDKs must not depend on the Toolkit at
runtime.

## Python Distribution Boundary

The `ext-reg` repository becomes a multi-package repository with at least these
independently versioned Python distributions:

- `inkcre-extension-toolkit`, initially `0.1.0`;
  - console entry point: `inkcre-ext`;
  - library-owned producer metadata readers, wheel/MF inspectors, Simple/static
    projection and multi-Extension preview builder;
  - developer publishing client and commands also move here because they run in
    developer/CD time.
- `inkcre-extension-registry`;
  - Registry Worker/service, repository, lifecycle, auth and UI;
  - no `inkcre-ext` console entry point;
  - depends on a compatible Toolkit library version for shared pure rules.

The existing local `preview.py` and CLI addition under
`inkcre_extension_registry` are implementation evidence, not the accepted
package layout. They must move before any release. Publishing Registry `0.2.0`
solely to deliver the preview CLI is rejected.

The Host SDKs remain independently released in their Peer-owned repositories:

- Core Python Host SDK/runtime in `core-py`;
- Web Host SDK in `@inkcre/core` in `client-web`.

## Consumer Package Management

Both Peer repositories use **PDM** to own the Developer Toolkit dependency and
lock, even though Client Web's application workspace remains pnpm:

The Registry service depends on the Toolkit base library only. Peer development
environments install the Toolkit's standard `cli` extra so `httpx`, Typer and
the `inkcre-ext` command do not become Worker runtime dependencies.

### Core

- add `inkcre-extension-toolkit` to a dedicated PDM development/tooling group;
- update the root `pdm.lock`;
- preview workflow installs that frozen group and runs `pdm run inkcre-ext ...`
  or the exact equivalent through the project environment;
- the preview workflow builds wheels and the static facade from its own verified
  exact-head checkout; Core checks do not upload its delivery input;
- Toolkit never enters the Core production/default runtime dependency set.

### Client

- add a root `pyproject.toml` and root `pdm.lock` for repository-level Python
  development tooling;
- keep the application and Extension workspace under pnpm;
- preview workflow installs the frozen tooling project and runs its
  `inkcre-ext` command;
- that same preview workflow builds the SPA and supplied MF snapshots and
  deploys the combined output directly; `Client checks` does not upload its
  delivery input;
- do not introduce uv, a Git dependency or a workflow-level commit pin.

This is not an attempt to make Client a Python application. A polyglot
repository may have a root Node workspace and a root PDM-managed development
tool environment with independent manifests and locks. Root placement is the
PDM happy path and avoids inventing a `tooling/` convention that current Client
does not have. Putting the project under `extensions/` is technically valid but
is not preferred: the lock and CLI serve repository-wide, multi-Extension
preview/CD, so that path would imply narrower source ownership than the tool
actually has.

## Release and Adoption Order

1. Move the local preview implementation into the independent Toolkit package.
2. Make Registry service imports point one way into the Toolkit pure library;
   keep Registry-only HTTP/storage/lifecycle code in the Registry package.
3. Run the existing Registry/package/Worker checks without adding tests.
4. Commit, push, review and merge the Toolkit/package split only with separate
   authorization.
5. Publish `inkcre-extension-toolkit 0.1.0` only with separate release
   authorization.
6. Add the released Toolkit to both repositories' root PDM project/lock.
7. Replace Client's Twitter-specific facade assembly and add Core's sibling
   Pages facade delivery. Each trusted preview workflow builds and deploys its
   own exact-head output; do not add checks-artifact handoffs.
8. Commit/push Peer changes and run PR #71/#65 preview acceptance only with the
   separately authorized remote operations.

No Registry service release is required merely to enable the Peer preview
facades. A later Registry release is needed only if its service package imports
the newly separated Toolkit at runtime or otherwise changes service behavior.

The current repository already publishes Python distributions as immutable
GitHub Release assets and has no PyPI publication authority. The shortest
release path therefore gives Toolkit its own `toolkit-v0.1.0` release unit and
wheel asset. Peer PDM manifests reference that versioned wheel URL and
`pdm.lock` records its content hash. This is a package-manager-owned immutable
release dependency, not a Git commit dependency; introducing a new PyPI
credential and publication lane is outside this slice.

The initial Toolkit split uses an ordinary compatible version requirement plus
the monorepo workspace source so the exact current-`main` revision can build and
publish the first Toolkit wheel without referring to an asset that does not yet
exist. After `toolkit-v0.1.0` is public, a small Registry metadata follow-up
replaces that bootstrap requirement with the same versioned wheel URL before
any standalone Registry service distribution is released. This avoids both a
404 build cycle and a Registry wheel that incorrectly expects Toolkit on PyPI.
