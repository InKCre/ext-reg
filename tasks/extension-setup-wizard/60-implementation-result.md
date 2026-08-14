# Implementation Result

## Outcome

The setup-wizard source implementation is complete in two task worktrees and
published for review as Draft PRs:

- Core: `feat/extension-setup-wizard-core` from
  `63f57b26ed8685fa34a74516ade39e2af72218d9`;
- Client: `feat/extension-setup-wizard-web` from
  `4fdc0832316d4489b9204b321cbe65b2c5ccb2e8`.

Review heads:

- Core commit `9f779b2`,
  https://github.com/InKCre/core-py/pull/52;
- Client commit `f25e684`,
  https://github.com/InKCre/client-web/pull/68;
- task packet initial commit `3fbb867aa6bdd00600bb811a97e22495b915707a`,
  https://github.com/InKCre/ext-reg/pull/13.

Admitted preview-controller corrections:

- Client [PR #69](https://github.com/InKCre/client-web/pull/69) was merged as
  `be2198f`. It separates the stable-Core
  `Database contract` check from the preview-producing `Workspace contract`
  without weakening production delivery or the intended merge gate, and it
  serves the exact checked Twitter Module Federation snapshot plus a read-only
  exact Release descriptor from the same PR preview origin.
- Core [PR #53](https://github.com/InKCre/core-py/pull/53) was merged as
  `22f3f40`. A Core PR preview now includes both Core API and PostgREST apps on
  the same isolated Neon branch and JWT trust boundary.

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
  Vitest: 21 files, 90 tests passed
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

## Preview Acceptance Evidence

The bounded black-box gate requested after implementation is now complete:

- Client PR #68 preview:
  `https://preview-client-web-pr-68.inkcre-client-web.pages.dev`;
- Core PR #52 API preview:
  `https://inkcre-core-py-pr-52-5989d607b441.herokuapp.com`;
- Core PR #52 PostgREST preview:
  `https://inkcre-postgrest-pr-52-0c434df03cac.herokuapp.com`;
- the isolated preview database contains `inkcre/twitter@0.2.0`, enabled for
  the preview Web Peer;
- the Client preview's same-origin exact Release and native
  `mf-manifest.json` both return successfully;
- a cold browser load restores and activates the Twitter Remote, renders the
  card action as `Set Up`, and opens `Set Up Twitter` with the four steps
  `Prepare`, `Connect account`, `Bookmark Source`, and `Review and start`.

The final cold-start defect was a UI/runtime ordering race: the Extensions view
could render before the app shell completed the initial Web Extension Host
restore. Client commit `f25e684` makes both callers share one startup Promise
and waits for that restore before listing cards. The full Client contract and
the live PR preview both passed after the correction.

The Client PR's independent `Database contract` check still fails against the
admitted stable Core v2 contract. That is intentional evidence that #68 cannot
merge before Core #52 is admitted and the generated Client contract is
refreshed; it no longer prevents the review Preview from deploying.

## Cleanup and Handoff

The task-owned Core Compose project, PostgreSQL volume, SSH tunnel/control
socket, runtime credentials/descriptors, generated contract staging files and
temporary Registry response were removed. The source-revision Docker image was
left as a normal reusable build cache, following the implementation plan; no
broad Docker prune was run.

Remaining actions:

1. Sir continues the wizard/provider acceptance from the live PR preview;
2. obtain Sir's review; do not merge Core #52 or Client #68 merely because the
   bounded entry-point acceptance passed;
3. after Core admission, regenerate Client evidence against admitted Core and
   satisfy the independent `Database contract` gate before Client admission;
4. publish `inkcre/twitter@0.2.0` and perform final delivery only under explicit
   later authorization.

## Client Selector and Settings Follow-up

Continued acceptance exposed that the native-Distribution cutover had removed
the former Extensions-page Client selector and that an earlier Settings
refactor had orphaned the all-Client management components. The authorized
follow-up restores both without changing the canonical Extension row or Host
contracts:

- the selected Client controls the card switch;
- this browser uses the local Web Host lifecycle;
- an addressable Client uses its generic Extension Host API;
- an unaddressable Client uses the existing atomic state-port RPC as durable
  desired state, with an explicit warning that a running remote process cannot
  be synchronously stopped;
- setup availability remains a contribution of this browser's running Web
  Distribution rather than the selected Client's switch state;
- Settings again lists and edits all registered Clients beneath a separate
  deployment scope.

The restored Client card also replaces its historical nonexistent inline-input
`confirm` event with an explicit, schema-validated update of an existing Client.
No create/delete lifecycle was added.
