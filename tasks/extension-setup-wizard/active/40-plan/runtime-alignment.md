# Implementation Plan — Runtime alignment

- **Status:** reviewed and ready; source not yet authorized
- **Authority:** active Impact Handshake
- **Supersedes:** plan `81`
- **Evidence:** active findings, inventories `78`/`80`, accepted D043

## Goal

Release two concrete Extension Host Runtimes from `ext-reg`, adopt them in Core
and Client, delete the embedded duplicates, and prove that Core can re-enable an
exact wheel already present in its interpreter without Registry availability.

The plan intentionally uses the existing rich-model style. It does not insert a
Repository, Store or generic Port between a Runtime and its Peer.

## Release Units

```text
ext-reg repository
  Registry service              inkcre-extension-registry
  Developer Toolkit             inkcre-extension-toolkit
  Core Python Host Runtime      inkcre-extension-runtime-core-py
  Client Web Host Runtime       @inkcre/extension-runtime-client-web
```

They release independently. The Registry service may reuse Toolkit pure native
serialization/inspection functions, but neither Runtime depends on the
Registry service or Toolkit CLI at runtime. Runtime package versions do not
replace the `core-py` / `@inkcre/core` Host SDK compatibility identity.

## Repository Shape

```text
contracts/                              # generated public schemas/OpenAPI
runtimes/
  core-py/
    pyproject.toml
    src/inkcre_extension_runtime_core_py/
    tests/
  client-web/
    package.json
    src/
    test/
toolkit/
src/inkcre_extension_registry/
```

Add `runtimes/core-py` to the existing uv workspace and
`runtimes/client-web` to the pnpm workspace. Root checks build and check all
four units. The historical `@inkcre/extension-runtime` target/digest API remains
retired; there is no compatibility package.

## Batch 1 — Contract pipeline and installed-wheel metadata

Owned repository: `ext-reg`.

### 1.1 Canonical contract source

Make `src/inkcre_extension_registry/contracts/models.py` the Pydantic source
for public Release/native association shapes instead of a compatibility import
from Toolkit. Keep FastAPI route models on those exact classes.

Extend `scripts/generate_contracts.py` to emit:

- current `contracts/openapi.json` and public JSON Schemas;
- `contracts/python-installed-extension.schema.json`;
- generated Pydantic v2 bindings for Toolkit and Python Runtime through
  `datamodel-code-generator`;
- generated TypeScript fetch/types/Zod v4 bindings for Web Runtime through
  `@hey-api/openapi-ts`.

Generated outputs are checked in. `contracts:check` regenerates into the normal
paths and fails when any output changes. Package type/build checks consume the
generated bindings. Remove handwritten duplicate Release/Distribution models
from Toolkit and, after adoption, Peer repositories.

Native semantic checks that JSON Schema cannot fully express—SemVer range
evaluation, PEP 440 mapping, URL-origin rules and MF closure rules—continue to
use the mature native libraries in the responsible consumer. They do not
redefine the object shape.

### 1.2 Installed metadata

Add this versioned record to every Core Extension wheel:

```text
<distribution>.dist-info/inkcre-extension.json
```

```json
{
  "schema_version": 1,
  "name": "inkcre/twitter",
  "version": "0.2.1",
  "host_sdk": {
    "name": "core-py",
    "version": ">=0.1.1 <0.2.0"
  },
  "python": {
    "project": "inkcre-ext-twitter",
    "project_version": "0.2.1",
    "entry_point": {
      "group": "inkcre.core.extensions",
      "name": "twitter",
      "object": "extensions.twitter:Extension"
    }
  }
}
```

It contains no Peer id, config, state, enabled, present, digest, target or
provenance. Toolkit compares it with the wheel filename, Core Metadata,
`entry_points.txt`, producer `[tool.inkcre-extension]` metadata and the prepared
Registry association.

### 1.3 Toolkit finalizer

Producers keep their normal PEP 517 build. Add one Toolkit command for an
already-built wheel:

```text
inkcre-ext python wheel finalize \
  --project <producer-pyproject.toml> \
  --wheel <input.whl> \
  --output-dir <empty-directory>
```

It uses the pinned `wheel` library's unpack/pack happy path, writes the record,
lets the library regenerate `RECORD`, inspects the completed output and only
then places it in the requested empty output directory. It does not invoke a
producer backend or support arbitrary build systems.

### 1.4 Files

- `src/inkcre_extension_registry/contracts/models.py`
- `scripts/generate_contracts.py`
- `contracts/openapi.json`, existing schemas and the new installed schema
- `toolkit/src/inkcre_extension_toolkit/{contracts,python_distribution,cli}.py`
- generated Toolkit bindings
- `src/inkcre_extension_registry/service/{python_distribution,app}.py`
- root/Toolkit manifests and `pdm.lock`
- root pnpm manifest/lock for the Web generator

### 1.5 Exit evidence

- contract generation leaves a clean diff on a second run;
- Registry, Toolkit and a generated Python/Web consumer compile;
- one real first-party wheel finalizes and its installed record agrees with
  standard wheel metadata;
- existing Registry/Toolkit checks pass.

## Batch 2 — Core Python Runtime + Core compatibility slice

Owned repositories: `ext-reg` and an explicitly authorized Core integration
worktree. The Runtime source remains owned by `ext-reg`; Core owns its model,
routes and composition changes.

### 2.1 Package

Create `inkcre-extension-runtime-core-py 0.1.0` with:

- `contracts.py`: generated Release/installed-record bindings plus native
  semantic validation;
- `release.py`: exact Release/Python association reader and Simple URL rules;
- `distribution.py`: installed discovery, pip planning/acquisition and file
  ownership checks;
- `modules.py`: standard entry-point discovery, origin validation and reversible
  module ownership;
- `base.py`: Core-specific `ExtensionBase`, bound model config/state behavior;
- `manager.py`: `ExtensionManager` orchestration and running-instance ownership;
- `errors.py`: Registry, compatibility, acquisition, entry-point, lifecycle and
  restart-required errors;
- `__init__.py`: the deliberate Extension-facing/Host-facing public exports.

### 2.2 Deliberate Core coupling

The package is Core-specific. `base.py` and `manager.py` import the lower
Core-owned `ExtensionModel` and concrete FastAPI/Source/Resolver/Peer APIs. They
do not use raw SQL and do not own schema/migrations. Core lower modules never
import Runtime; `run.py`, routes and other composition modules import Runtime
afterward.

This is an explicit **host-provided import contract**, not a hidden
package-manager dependency. The Runtime wheel does not declare a fictional
published `core-py` dependency, and Core is the only supported executable host.
The pure Release/distribution/module portions remain independently checkable in
ext-reg. Package release readiness additionally installs the built wheel into a
temporary checkout/worktree of a compatible Core revision and runs the real
manager/base import and lifecycle integration. It is not simulated behind a
new adapter, fixture Host or generic Port.

### 2.3 Active Record API consumed by Runtime

The Core adoption supplies these behaviors on the existing `ExtensionModel`:

- class-level `list`, `get` and `install`;
- instance `uninstall` and exact version update;
- instance `enable_peer` / `disable_peer`;
- instance `update_config`, `read_state`, `mutate_state`,
  `mutate_config_and_state` and `update_config_schema`.

Method implementations own their transaction/locking rules. Runtime passes
business values and consumes updated model instances; it never mirrors row
fields in a Store DTO.

`ExtensionBase` binds the current model and exposes validated config/state
operations to the Extension. It remains distinct from SQLModel inheritance
because code type and persisted row have different lifetimes, but together they
form the same rich Extension aggregate.

### 2.4 Manager behavior

`ExtensionManager` owns `list/get/install/uninstall/enable/disable`, config and
Extension-management dispatch, startup restore and shutdown. Core routes call
it rather than reimplementing those state machines.

Enable/cold restore sequence:

1. load the deployment-installed `ExtensionModel`;
2. scan installed metadata for exact name/version;
3. require exactly one owner of the normalized Python project and verify its
   standard metadata/entry point/files/Host SDK compatibility;
4. on exact hit, do not resolve Registry origin and do not perform network/pip;
5. on miss, resolve the one-operation Core Registry origin once, fetch the exact
   Release, acquire with the standard pip path, then rediscover;
6. load the entry point, bind `ExtensionBase` to the model, claim/publish/start;
7. persist enabled intent through the model;
8. compensate lifecycle/publication/module ownership if persistence fails.

Install or version change remains Registry-authorized; it does not infer a new
deployment Release merely from locally present bytes. Pip dependency preflight,
prohibition on replacing Core-owned/loaded distributions and restart-required
semantics remain intact.

### 2.5 Core compatibility integration

Before publication, use the locally built Runtime wheel and locally built
Toolkit wheel in a disposable Core environment:

- restore the whole-row behavior from `app/business/extension/state.py` onto
  the existing `app/schemas/extension/main.py::ExtensionModel` Active Record;
- remove `ExtensionStore`/`SQLExtensionStore` and the duplicate installed-row
  projection where the model can serialize with secret `state` excluded;
- migrate first-party `ExtensionBase` imports to the Runtime public API;
- replace embedded manager/base/Release/distribution/publication orchestration
  with the Runtime manager while keeping Core routes/bootstrap as composition;
- build first-party wheels normally, then finalize/inspect them with the local
  Toolkit;
- delete migrated duplicates only after the local Runtime wheel passes the
  same repository's focused tests.

The mandatory pre-publication gate is run from a disposable Core checkout so it
does not commit a local path dependency:

```text
PDM 2.27.0 pdm install --frozen-lockfile
PDM 2.27.0 pdm run python -m pip install --no-deps --force-reinstall \
  "$RUNTIME_WHEEL"
PDM 2.27.0 pdm run pytest \
  tests/test_extension_runtime_package.py \
  tests/test_extension_registry_runtime.py \
  tests/test_extension_distribution.py
PDM 2.27.0 pdm run check
```

`tests/test_extension_runtime_package.py` is the explicit new consumer gate. It
imports Runtime `base`/`manager` from the installed wheel and executes one
concrete model/lifecycle path; the other two files retain native-consumer and
compensation coverage.

### 2.6 Exit evidence

- Runtime pure package checks pass and its wheel builds;
- the built wheel installs into the compatible Core environment, imports its
  Host-provided modules and executes one manager/base lifecycle;
- exact local hit performs zero Registry-origin/HTTP/pip calls;
- local miss follows exact Release/Simple/pip and rediscovery;
- malformed/ambiguous installed records fail closed;
- module load/unload restores owned module state;
- Core integration proves manager/base/contribution lifecycle, rich-model
  behavior, state confidentiality and enable/disable compensation before the
  package is eligible for publication.

## Batch 3 — Client Web Runtime + Client compatibility slice

Owned repositories: `ext-reg` and an explicitly authorized Client integration
worktree. Runtime package ownership remains in `ext-reg`; Client owns its rich
model, Peer delegation, UI and composition changes.

### 3.1 Package

Create `@inkcre/extension-runtime-client-web 0.1.0` with:

- generated Registry fetch/types/Zod bindings;
- `registry.ts` for exact Release/MF resolution and URL materialization;
- `manager.ts` for install/enable/disable/startup/shutdown and volatile running
  state;
- `module.ts` for native MF registration/load and the existing
  initialize/activate/deactivate/dispose sequence;
- `errors.ts` and explicit public exports.

### 3.2 Deliberate Client coupling

The package has a peer dependency on the compatible `@inkcre/core` Host API and
uses its concrete rich Extension model and Extension module types. The Client
application supplies its existing concrete Module Federation Host instance;
the Runtime types that value with the mature MF library API rather than an
InKCre-defined generic Port. The Runtime does not create a second MF runtime
copy.

Client application composition owns selected-Peer delegation, Registry-origin
policy input, shell/UI and popup presentation. The Runtime owns the manager
state machine and returns the loaded Extension module, whose setup contribution
is still defined by `@inkcre/core` and rendered by Client.

### 3.3 Behavior

- use generated Release parsing and Zod validation;
- precheck `@inkcre/core` Host SDK compatibility before MF load;
- register/load the native manifest through the concrete MF Host;
- execute and compensate the four Web lifecycle hooks;
- persist enabled intent through the concrete rich model only after activation;
- deactivate before durable disable, restoring runtime if persistence fails;
- keep Web `present` session-local; do not adopt Python installed-wheel logic.

### 3.4 Client compatibility integration

Before publication, pack the local Runtime and install it into a disposable
Client checkout beside the exact compatible `@inkcre/core` workspace package.
In the Client source slice:

- retain/refactor the project-standard rich Extension model consumed directly
  by Runtime; do not add a repository interface;
- move embedded manager/Registry/MF lifecycle code out of
  `packages/core/src/extension/{host,registry,module-federation}.ts`;
- keep generated database transport, selected-Peer delegation, Registry-origin
  policy, UI, popup shell and Twitter setup contribution in Client;
- wire the existing MF Host instance from application composition;
- remove handwritten Release Zod models and delete embedded duplicates only
  after local-tarball integration passes.

Mandatory pre-publication gate:

```text
pnpm install --frozen-lockfile
pnpm --dir "$EXT_REG_ROOT" --filter @inkcre/extension-runtime-client-web pack \
  --pack-destination "$RUNTIME_PACK_DIR"
pnpm --filter @inkcre/client-web add --offline --save-exact "$RUNTIME_TARBALL"
pnpm exec vitest run --project runtime \
  packages/core/src/extension/runtime-adoption.test.ts \
  packages/core/src/extension/postgrest-state.test.ts
pnpm exec vitest run --project client-web \
  apps/client-web/src/twitter-setup-wizard.spec.ts \
  apps/client-web/src/views/extensions/extensions.spec.ts
pnpm check
```

These commands run in a disposable Client checkout. The new
`runtime-adoption.test.ts` exercises the packed package with the concrete
`@inkcre/core` model and MF Host. The batch must not commit the temporary
absolute tarball dependency.

### 3.5 Exit evidence

- npm package checks and pack succeed;
- the packed tarball installs beside the compatible packed/workspace
  `@inkcre/core` and executes the concrete consumer integration;
- exact Release/MF parsing comes only from generated bindings;
- concrete locked MF Host integration exercises register/load and lifecycle;
- package contains no PostgREST transport implementation, router, popup or
  application UI.

## Batch 4 — Independent package publication

Owned repository: `ext-reg`; every remote mutation requires explicit approval.

1. release Toolkit `0.2.0`;
2. release Python Runtime `0.1.0` as a wheel consumable by PDM;
3. release Web Runtime `0.1.0` as an npm tarball/package consumable by pnpm;
4. record independent versions/assets and normal package checks;
5. do not couple package publication to Registry service deployment.

Add a package-release workflow only if it follows the repository's existing
release governance and native package-manager happy path. Do not add artifact
handoff, public-byte replay or provenance machinery merely for this batch.

## Batch 5 — Released dependency normalization

Owned repositories: Core and Client integration worktrees; explicit
cross-repository mutation remains required.

1. replace the disposable/local Toolkit and Runtime inputs with the released
   assets in Core `pyproject.toml`/`pdm.lock` and Client
   `package.json`/`pnpm-lock.yaml`;
2. prove frozen package-manager installation from a clean environment;
3. rerun the exact integration gates and each repository's full check;
4. confirm no local path/workspace override or duplicate embedded Runtime code
   remains;
5. only then commit/push the adoption branches when separately authorized.

The lock-normalization static red line is:

```text
! rg -n 'inkcre-extension-(runtime-core-py|toolkit).*(path|editable|file:)' \
  pyproject.toml pdm.lock
! rg -n '@inkcre/extension-runtime-client-web.*(file:|link:|workspace:)' \
  package.json pnpm-lock.yaml
```

If a package-manager lock uses a different native representation, replace this
text check with its native lock inspection rather than broadening the regex.

## Batch 6 — Preview acceptance

1. rebuild Core PR #65's sibling static Registry with finalized first-party
   wheels and the released Toolkit;
2. rebuild Client PR #71 with the released Web Runtime;
3. deploy through the normal preview workflows;
4. prove Core local-hit offline re-enable and fresh-environment Registry miss;
5. connect Client to Core, enable Twitter and open the setup popup;
6. stop for Sir's product acceptance.

Automation may use provider deployment success and short non-404 probes. It
must not reintroduce artifact-wide downloads, byte equality, cache-busters,
digest URL substitution or long retries.

## Verification Commands

### ext-reg

```text
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
pnpm contracts:check
focused Toolkit/Python Runtime/Web Runtime checks
pdm build
pnpm --filter @inkcre/extension-runtime-client-web pack
pnpm check
git diff --check
```

### Core

```text
PDM 2.27.0 pdm lock --check
focused Active Record, Runtime lifecycle and local-first tests
build/finalize/inspect all first-party wheels
PDM 2.27.0 pdm run check
git diff --check
```

### Client

```text
pnpm install --frozen-lockfile
focused Runtime adoption, MF and Twitter setup tests
pnpm check
actionlint on changed workflows, if any
git diff --check
```

## Deletion Gates

- no handwritten consumer Release model is deleted until generated bindings
  build in that consumer;
- no embedded Peer manager/base/consumer is deleted until the locked Runtime
  passes the same repository's focused lifecycle tests;
- no Store abstraction survives Core adoption merely as a compatibility shim;
- no historical generic target/digest Runtime API is restored;
- no package is published, Peer repository mutated, preview deployed or PR
  merged without its separate authorization.

## Explicit Non-goals

- database `present`/`running` state or peer-binding relation;
- one universal Python/Web lifecycle or model interface;
- Repository, Persistence Port, Contribution Port or a fourth support-contract
  release unit;
- detached Extension development independent of its Peer implementation;
- arbitrary producer build-backend support inside Toolkit;
- Runtime ownership of application UI or remote-Peer selection;
- production Registry deployment as a prerequisite for static PR previews;
- deep public artifact verification or new consistency/security machinery not
  required by the observed defect.
