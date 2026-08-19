# Extension Host Runtime Family — Current Inventory

> **Evidence only:** the file inventory remains useful, but D043 supersedes its
> ownership classification where it keeps manager/base lifecycle or a Store in
> the Peer. Use the active Handshake and plan for implementation ownership.

## Baselines

This inventory is read-only evidence from:

- `ext-reg` current main/worktree and tags `v0.1.0` through `v0.1.3`;
- Core feature worktree
  `/Volumes/WorkSSD/Development/InKCre/.worktrees/core-py-extension-setup-wizard-peer`;
- Client feature worktree
  `/Volumes/WorkSSD/Development/InKCre/.worktrees/client-web-extension-setup-wizard-peer`.

It classifies ownership before extraction. It does not authorize source changes,
publication or cross-repository mutation.

## ext-reg Package History

Current `ext-reg` has two release units:

- Registry service: root Python distribution `inkcre-extension-registry 0.2.0`;
- Developer Toolkit: `toolkit/`, Python distribution
  `inkcre-extension-toolkit 0.1.0`.

The root is one uv workspace with `toolkit`; pnpm currently pins repository and
Wrangler tooling but owns no TypeScript workspace package.

Tags `v0.1.0`–`v0.1.3` did contain
`packages/runtime-web`, published as `@inkcre/extension-runtime`. That package
established the correct repository ownership but the wrong abstraction: it
exposed generic targets, target digests, condition matching and artifact paths
that were removed by the native Distribution cutover. Its lifecycle controller
is evidence, not an API to restore unchanged. The package was removed in
`bd559aa` when native Python and Module Federation Registry surfaces replaced
the generic target protocol.

The new Runtime packages therefore use explicit names and native contracts;
they do not silently republish the historical API.

## Core Embedded Runtime

### Extract to the Core Python Runtime

| Current Core surface | Runtime responsibility |
| --- | --- |
| `app/business/extension/release.py` | exact Release/Python association values, Registry reader, native association and Host SDK precheck, Simple URL validation |
| `app/business/extension/distribution.py` | installed Distribution discovery, pip download/preflight/install, wheel/file ownership checks, entry-point discovery, module origin validation and load/unload |
| selected errors in `app/business/extension/errors.py` | Registry, compatibility, acquisition, entry-point, runtime and restart-required failures |
| selected orchestration in `app/business/extension/main.py` | local-first prepare, Registry fallback and native module load/unload handle |

Tests that primarily move with those surfaces are
`tests/test_extension_distribution.py` and the Release/native-consumer portions
of `tests/test_extension_registry_runtime.py`.

### Remain Core-owned

| Core surface | Preserved authority |
| --- | --- |
| `app/business/extension/state.py` | `InstalledExtension`, SQL store, config/state and atomic enabled persistence |
| `app/business/extension/main.py` | deployment install/uninstall/version/config commands, Peer management/delegation, enable/disable persistence ordering, startup/shutdown coordination, `ExtensionBase` Host SDK lifecycle and compensation |
| `app/business/extension/runtime.py` | Core publication adapter for FastAPI, Source, Resolver and Peer inbound contributions |
| `app/business/extension/config.py` | executing Peer override → deployment config → process fallback Registry-origin policy |
| `app/routes/extension.py`, Peer modules and `run.py` | management transport, HTTP error mapping, lease/capability behavior and process bootstrap |

The current defect is exact: `ExtensionHost._acquire()` resolves the Registry
before `PipDistributionConsumer.acquire()` calls
`AcquiredDistribution.discover()`. Local discovery exists but is sequenced too
late.

The current wheel contains standard Core Metadata and `entry_points.txt`, while
producer-only identity remains in `[tool.inkcre-extension]`. Without additional
installed metadata, a fresh process cannot prove canonical Extension Name and
Host SDK range without the Registry.

## Client Embedded Runtime

### Extract to the Client Web Runtime

| Current Client surface | Runtime responsibility |
| --- | --- |
| `packages/core/src/extension/registry.ts` | exact native Release/MF association parser and Registry reader |
| runtime portions of `packages/core/src/extension/host.ts` | SDK precheck, MF prepare/activate/deactivate, module/lifecycle compensation and volatile running/error state |
| `packages/core/src/extension/module-federation.ts` | structural MF consumer port; the concrete global wrapper is replaced by injection |
| runtime hook types in `packages/core/src/extension/model.ts` | structural Web lifecycle hooks only; no Vue/setup type |

The Runtime package must not depend on a concrete Module Federation runtime.
The current Client lock contains MF runtime `0.17.1`, `0.21.6` and `0.22.1`
through different producers; injection prevents the Runtime package from adding
another copy.

### Remain Client-owned

| Client surface | Preserved authority |
| --- | --- |
| `packages/core/src/extension/state.ts` and `postgrest-state.ts` | deployment Extension state port and PostgREST/RPC persistence |
| `packages/core/src/extension/registry-origin.ts` | Peer/deployment/public Registry-origin policy |
| Client-owned coordinator in `host.ts` | runtime-before-enable, cleanup-before-disable and persistence compensation |
| setup contribution in `packages/core/src/extension/model.ts` | Vue component contribution and Client Host SDK projection |
| `apps/client-web/src/core.ts` and `main.ts` | concrete MF Host instance, Peer runtime and application bootstrap |
| `apps/client-web/src/extension-peer-control.ts` | selected Peer, live delegation and desired-state-only control |
| Extension views/cards/setup dialog/settings | application UI, popup shell, config and Peer selection |

Web `present` is only a browser/MF-session observation. It is not Python-style
installed-wheel presence and is not persisted.

## Cross-unit Contract Inventory

Toolkit currently owns Pydantic models for:

- canonical Extension Name and strict SemVer;
- exact Release records;
- Python and Module Federation associations;
- Host SDK SemVer ranges and Python entry points.

Registry service imports those pure Toolkit models through compatibility
modules. Generated JSON Schemas and OpenAPI are the language-neutral public
truth. The Python Runtime must not depend on the Developer Toolkit merely to
parse production metadata, and the Web Runtime must not import Python code.

The implementation therefore adds one generated installed-wheel schema under
`contracts/` and packages native parsers with each Runtime. Existing contract
generation/checks prevent drift without inventing a fourth product unit or a
cross-language lifecycle library.

## Boundary Result

```text
Core database/Peer/publication adapter
  -> Core Python Runtime
       -> local installed wheel metadata
       -> Registry/Simple/pip only on local miss

Client state/Peer/UI coordinator
  -> Client Web Runtime
       -> exact native Release reader
       -> injected Module Federation Host

Registry service and Developer Toolkit
  -> language-neutral generated contracts
  -> native admission/build rules
```

No database `present`, peer binding, generic target matcher, universal lifecycle
or Runtime-to-Peer reverse dependency is required.
