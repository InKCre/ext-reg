# Cross-repository Implementation Plan

## Status

**Accepted for execution.** This plan maps the completed product/HLD contract to
three fresh repositories and orders delivery so that every intermediate state is
safe. Exact filenames may move only when repository conventions prove a better
owner; the authority and verification mapping must not drift.

## Release Coordinate And Acceptance Target

- Registry package: `inkcre/twitter@0.1.0`.
- Web target key: `web-module-federation-v1`.
- Python target key: `python-core-v1`.
- Both targets use the same Extension Version and different target digests.
- Registry, Python runtime package, and Web runtime package begin at contract
  version `0.1.0`; lifecycle API capability is `1.0.0`.

## Repository And Branch Topology

1. Initialize and publish the existing `ext-reg` main branch as public
   `InKCre/ext-reg` after its first coherent foundation commit.
2. Fetch current peer remotes and create durable, separate worktrees from exact
   `origin/main`:
   - `core-py`: `feat/extension-registry-mvp`;
   - `client-web`: `feat/extension-registry-mvp`.
3. Never modify either user's existing peer worktree. Each repository gets its
   own commits, PR, required checks, and protected-main merge.
4. Delivery order is `ext-reg` → `core-py` → `client-web`. The client consumes the
   database contract from the published core image, so reversing the final two
   would create an unverifiable generated schema.

## `ext-reg` Implementation Surface

### Foundation

- Root: `pyproject.toml`, `uv.lock`, `.python-version`, `package.json`,
  `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `README.md`, `CONTRIBUTING.md`,
  `ARCHITECTURE.md`, `FILESYSTEM.md`.
- Pin Python 3.13, Node 22.22.3, `uv`, and pnpm. One `check` command runs contract
  generation checks, formatting, lint, type checks, focused tests, and builds.
- Extend `AGENTS.md` and `docs/index.md` only outside SVC-managed blocks.

### Python package and Worker

- `src/inkcre_extension_registry/contracts/`: target/release models, canonical
  JSON, SemVer/profile matching, lifecycle state machine, and conformance data.
- `src/inkcre_extension_registry/client.py`: typed anonymous/publisher HTTP
  client shared by CLI and core adapter.
- `src/inkcre_extension_registry/cli.py`: deterministic target assembly, blob
  upload, target association, publication, and public smoke commands.
- `src/inkcre_extension_registry/service/`: FastAPI routes, bearer auth,
  D1 repository, R2 blob access, and problem responses.
- `src/inkcre_extension_registry/worker.py`: minimal ASGI/Worker entry point.
- `migrations/0001_registry.sql`: namespaces, credentials, extensions, releases,
  and targets with unique/foreign-key/state constraints.
- `wrangler.jsonc`: production D1/R2 bindings, Python flags, observability, and
  Node-22-compatible pywrangler deployment.

### Language-neutral and Web Runtime/API

- `contracts/`: canonical target/release schemas, compatibility vocabulary,
  lifecycle transition fixture, OpenAPI, and a machine-readable contract
  revision file. Generated files are checked, not hand-edited.
- `packages/runtime-web/`: `@inkcre/extension-runtime`, a small TypeScript
  package containing Registry client/models, compatibility selection,
  lifecycle controller, and `ExtensionModule` interface. It has no UI code.
- Python and TypeScript lifecycle/compatibility implementations execute the same
  committed fixture.

### Critical verification only

- Unit-level checks cover canonicalization/path safety, matcher semantics, and
  lifecycle transitions.
- One black-box Registry E2E against local pywrangler covers unauthorized
  publish, two independent target appends, explicit publication, anonymous read
  and byte download, identical retry, and conflicting overwrite.
- No broad abuse, fuzz, malware, mirror, or account-management test suite.

### Delivery

- `.github/workflows/ci.yml`: frozen Python/Node installs and the single check.
- `.github/workflows/release.yml`: after exact successful current-main CI,
  publish the Python wheel as GitHub Release `v0.1.0` and
  `@inkcre/extension-runtime@0.1.0` to GitHub Packages.
- `.github/workflows/production.yml`: apply forward D1 migrations and deploy the
  exact verified Worker revision using Cloudflare environment secrets.
- Production resources:
  - Worker `inkcre-extension-registry`;
  - D1 `inkcre-extension-registry-production`;
  - private R2 `inkcre-extension-registry-production`;
  - public Workers.dev origin unless a zero-risk existing custom domain is
    already available.
- Manually seed namespace `inkcre` and separate hashed credentials for the two
  peer repositories; write raw tokens only to their GitHub secrets.

## `core-py` Implementation Surface

### Dependency and generated contract

- Add the exact ext-reg Python wheel release URL to `pyproject.toml`/`pdm.lock`.
- Add a contract revision check/fixture under `tests/extensions/` so core's
  adapter cannot silently drift from the ext-reg lifecycle and target model.

### Deployment database

- Add SQLModel records under `app/schemas/extension/` for
  `extension_installations` and `extension_peer_bindings`.
- Add one append-only Alembic migration with composite keys, binding foreign key,
  exact target digest fields, and PostgREST-compatible privileges/ownership.
- Add both tables to database contract constants, raw schema/runtime-contract
  export, ACL/readiness, reset ordering, migration history, and schema tests.
- Do not drop or reinterpret the legacy `extensions` table in MVP. It remains a
  built-in artifact catalog during transition but no longer drives Runtime
  installation.

### Runtime adapter

- Refactor `app/business/extension/main.py` around the ext-reg lifecycle runner,
  Registry client/matcher, new installation/binding records, and an admitted
  bundle catalog embedded in the image.
- Fix the current running-map key bug and add dynamic route unpublication so
  disable removes observable runtime side effects.
- Startup loads only peer bindings for the current core UUID. Artifact scanning
  must never create an installation or resurrect an uninstall.
- Enable resolves a compatible published Python target and requires its target
  digest in the embedded admitted catalog before importing code; after startup it
  inserts the binding. Disable closes/unpublishes before deleting the binding.
- Update `app/routes/extension.py` to namespaced install-aware list/config and
  core-local enable/disable semantics. Deployment install/uninstall themselves
  use the shared PostgREST tables and FK transaction boundary.
- Add a canonical public Registry URL setting with an environment override.

### Python target artifact and image

- Add `extensions/twitter/target-publish.json` with the accepted coordinate,
  target key, entry point, and controlled conditions.
- Add a deterministic stdlib build script producing a zip containing
  `extensions/__init__.py` and `extensions/twitter/**` with fixed metadata.
- The ext-reg CLI creates the canonical target manifest and digest from that zip.
- Modify `Dockerfile` to copy the exact zip/manifest into an admitted-artifacts
  directory. Runtime imports only a bundle whose manifest digest matches the
  selected binding; dependencies remain in the frozen root lock.

### Core tests and CD

- Focus tests on install-disabled state, compatible admitted enable, missing or
  mismatched digest rejection without a binding, lifecycle close/route removal,
  disabled uninstall persistence, and container catalog presence.
- Extend the exact-main artifact workflow: build target → build/push application
  image containing it → publish/append the same target through ext-reg CLI.
- Store Registry origin and scoped token as repo variable/secret; record source
  revision, target key, and digest in the workflow summary.

## `client-web` Implementation Surface

### Runtime/API adoption

- Add `@inkcre/extension-runtime@0.1.0` from GitHub Packages.
- Refactor `packages/core/src/extension/base.ts` to use the ext-reg Registry
  client, matcher, lifecycle controller, namespaced coordinate, and exact target
  digest URL. Remove the hard-coded `/{id}/client-web/remoteEntry.js?version=`
  convention and local duplicate lifecycle contract.
- Read `extension_installations` plus `extension_peer_bindings`; one installation
  object combines its per-peer bindings. Presence of the selected peer binding
  replaces the legacy UUID array.
- Local Web enable loads/initializes/activates from the immutable artifact prefix
  before inserting its binding. Local disable deactivates/disposes then deletes
  only its binding. Remote core enable/disable uses its namespaced core route.
- Install looks up an exact published Registry release and inserts only the
  installation row. Uninstall deletes it and relies on the binding FK to reject
  enabled removal.

### UI, schema, and first-party target

- Regenerate database types/runtime contract from the released core image.
- Update install UI to `namespace/name` + exact version, cards to show canonical
  coordinate/binding, and add uninstall with a clear enabled-state failure.
- Make the public Registry origin the default ClientConfig value while preserving
  an operator override.
- Change Twitter Vite base to `./`, stable build target to ES2022, and
  `@inkcre/core` shared version from the contradictory `0.0.0` placeholder to the
  actual package version.
- Add `extensions/twitter/target-publish.json` with Web integration/lifecycle/MF
  share-scope/Vue/core/ECMAScript conditions.

### Web tests and CD

- Reuse ext-reg runtime-package fixtures; add focused host tests for exact target
  selection, no-binding-on-load-failure, successful binding after lifecycle, and
  uninstall guard.
- Add one browser integration proving the published-style remote prefix loads
  and runs; do not duplicate the entire application E2E matrix.
- Extend exact-main Pages workflow: build core package and Twitter remote, publish
  the target through the pinned ext-reg CLI, then continue the existing exact
  Pages build/deploy. Store the scoped token as a repo secret.

## Merge And Production Order

1. Commit ext-reg foundation/service/contracts, create public remote, run CI.
2. Create production D1/R2, seed namespace/credentials, deploy Worker, run public
   Registry E2E, and publish runtime packages/release.
3. Implement core in its fresh worktree, run full core checks, push PR, merge only
   after required checks, then wait for exact-main image publication, target
   publication, migration, and production deployment.
4. Implement client against that immutable core schema/image and ext-reg Web
   package, run full client checks, push PR, merge, then wait for target
   publication and Pages deployment.
5. Confirm Registry release has both target keys/digests, then execute production
   lifecycle acceptance and preserve machine-readable observations in this task.

## Commit Boundaries

- ext-reg: foundation/contracts/service/tests as one coherent initial commit;
  delivery/production configuration may be a second commit if needed.
- core-py: database contract migration; runtime/admission; target/CD, each as a
  reviewable commit when their tests pass.
- client-web: generated contract/runtime integration; UI/target/CD, each as a
  reviewable commit when their tests pass.
- Never include existing user changes, generated secrets, local Wrangler state,
  temporary PoCs, or unrelated formatter churn.
