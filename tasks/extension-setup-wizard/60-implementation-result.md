# Implementation Result

## Outcome

The setup-wizard source implementation is complete in two task worktrees and
published for review as Draft PRs:

- Core: `feat/extension-setup-wizard-core` from
  `63f57b26ed8685fa34a74516ade39e2af72218d9`;
- Client: `feat/extension-setup-wizard-web` from
  `4fdc0832316d4489b9204b321cbe65b2c5ccb2e8`.

Review heads:

- Core commit `e9bec66f8e42e19c8310cf7623bc17fbbcb2132f`,
  https://github.com/InKCre/core-py/pull/52;
- Client commit `5cde5f0685873d63d897299febe6f7c2b66a970f`,
  https://github.com/InKCre/client-web/pull/68;
- task packet initial commit `3fbb867aa6bdd00600bb811a97e22495b915707a`,
  https://github.com/InKCre/ext-reg/pull/13.

Follow-up delivery correction:

- Client workflow commit `07ec71b` is under review at
  https://github.com/InKCre/client-web/pull/69. It separates the stable-Core
  `Database contract` check from the preview-producing `Workspace contract`
  without weakening production delivery or the intended merge gate.

No ext-reg service source change was necessary. The Registry continues to own
the Python wheel and Module Federation Distribution associations only.

## Core Result

- Added canonical deployment-wide `extensions.state JSONB`, database contract
  v3 and migration head `c7d8e9f0a1b2`.
- Kept state mutation inside Core/PostgreSQL row-lock operations; authenticated
  PostgREST may read state inside the accepted Peer boundary but cannot write it.
- Added typed fresh config/state operations to `ExtensionBase` without exposing
  `ExtensionModel` to an Extension.
- Added lifecycle-bound exact public HTTP route claims; only the running
  Twitter callback bypasses Peer JWT, and route withdrawal removes the bypass.
- Implemented durable Twitter OAuth App/account/transaction state with Authlib,
  PKCE S256, standalone Core callback HTML, polling projection, disconnect,
  Bookmark Source selection/creation and Finish/initial collection.
- Made provider token refresh conditional on the exact prior durable token;
  provider OAuth/401 rejection marks that authorization as requiring reconnect
  without erasing the account or its Sources.
- Made Finish reuse or create the exact non-failed initial collection job under
  Source-owned PostgreSQL serialization, so retries and concurrent Core Peers do
  not create duplicate starts.
- Advanced Core Host SDK to `0.1.1` and the Twitter Python wheel to `0.2.0`.
- Preserved Source authority: uninstall does not inspect/delete Sources, while a
  deleted formerly selected Source makes setup incomplete instead of producing
  false readiness.

Implementation refinements from the HLD examples:

- Twitter commands return a compact refreshed `TwitterSetupStatus` projection
  rather than several command-specific wrapper objects; Begin remains `201`.
- Disconnect returns the refreshed projection (`200`) so Web does not need a
  second read after a successful command.
- Selecting an existing Bookmark Source does not edit it implicitly; schedule
  editing stays on the Sources surface. Creating a Source still accepts the
  setup schedule.
- The exact public-route claim lives with the existing reversible runtime
  publication primitives rather than in another shallow module.

## Client Result

- Added optional `ExtensionSetupContribution` to the running Web Extension
  module contract. The Host exposes it only while that exact runtime is active.
- Added the Extension-card Setup action and `InkDialog` shell. Before disable,
  the shell clears the contributed component and waits one Vue tick before the
  Host unloads the Remote.
- Extended the existing authenticated `Client.request` path with `AbortSignal`,
  preserved body/headers/signal through its one-time 401 retry and surfaced
  bounded string FastAPI `detail` errors.
- Added the Twitter-owned four-step wizard: Prepare Core, configure OAuth App
  and connect X, choose/create Bookmark Source, review/start.
- The wizard discovers reachable Core Peers, requires explicit enablement,
  shows the selected Core callback URL, opens X deliberately in another tab and
  polls only the opaque transaction projection. Closing/unmounting aborts all
  wizard requests and polling.
- Advanced `@inkcre/core` to `0.1.1`, Twitter Web to `0.2.0`, and generated the
  database types/runtime evidence from Core contract v3.

## Verification Evidence

Core:

```text
PDM_IGNORE_ACTIVE_VENV=1 uv tool run --from pdm==2.27.0 pdm run check
  migration checks: 31 + 23 passed
  format/lint/type checks: passed, 0 diagnostics
  pytest: 241 passed
git diff --check: passed
```

Client:

```text
pnpm check
  format/lint/type checks: passed
  Vitest: 21 files, 88 tests passed
  all workspace builds and package contract: passed
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 .github/workflows/*.yml
  passed
git diff --check: passed
```

Cross-repository contract:

```text
Core development image -> contract revision peer-database-runtime-v3
Client contract:sync -> passed
Client contract:check against exact task-built image
  sha256:1159b60622cf3b24caa32a037d8c28ffaef79262523f7dd2565393e1b09d2dfd
  -> passed
Generated extensions relation includes state; generated contract reports v3
```

The contract artifact was exported from the migrated task-owned PostgreSQL
runtime using the same schema/role/runtime-contract packaging path as CI, then
embedded in the final task image. Checkout-only generated SQL/JSON staging files
were removed after Client verification, as required by the Core repository
contract.

Read-only Registry check:

```text
GET https://registry.inkcre.dev/v1/extensions/inkcre/twitter/releases/0.2.0
404 {"detail":"public Release does not exist"}
```

## Cleanup and Handoff

The task-owned Core Compose project, PostgreSQL volume, SSH tunnel/control
socket, runtime credentials/descriptors, generated contract staging files and
temporary Registry response were removed. The source-revision Docker image was
left as a normal reusable build cache, following the implementation plan; no
broad Docker prune was run.

Remaining actions:

1. admit Client workflow PR #69, updating branch protection to require the new
   `Database contract` context, then sync Client #68 with `main`;
2. let the Draft PR check suites finish and address attributable failures;
3. obtain Sir's review; do not mark ready, merge, publish or deploy merely
   because checks pass;
4. after Core admission, regenerate Client evidence against admitted Core before
   making Client merge-ready;
5. run real-X/black-box acceptance only when Sir resumes that deferred gate;
6. publish `inkcre/twitter@0.2.0`, deploy or merge only under explicit later
   authorization.
