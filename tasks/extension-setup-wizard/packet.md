# Extension Setup Wizard

- **Objective**: Design a coherent post-install setup experience for InKCre
  Extensions, using `inkcre/twitter` as the first vertical slice: guide a user
  from an installed Release to a verifiably usable deployment-wide
  whole-Extension setup through `client-web`, without collapsing Registry,
  deployment, Peer runtime, Extension configuration, durable Extension state,
  Source configuration/state, and runtime memory into one concept.
- **Guardrails**: This packet is a cross-repository control surface, not durable
  product authority; the Extension Registry continues to own Releases and
  Distributions only; do not change source code or project state before an
  implementation-ready plan and Sir's explicit start; treat Sir's statements
  and agent proposals as reviewable hypotheses; discuss one bounded product
  question at a time; report the previous result before advancing; group small
  adjacent questions; record decisions continuously; do not force different
  Host SDKs into one setup or lifecycle model; do not claim setup completion
  when required credentials or runtime state disappear on restart.
- **Verification**: Product design defines the setup entry point, completion
  condition, ownership of every step and value, interruption/resume behavior,
  multi-Peer behavior, and failure/recovery UX. HLD then provides exact
  language-neutral cross-Peer contracts plus Web/Core-specific Host SDK shapes,
  and an implementation plan maps repositories, files, migrations, tests,
  delivery order, and review evidence before any source mutation starts.
  The Twitter vertical slice must eventually prove install -> per-Peer enable ->
  card entry -> popup wizard -> OAuth App configuration -> durable account OAuth
  -> required initial resources -> Extension readiness -> restart/resume, with
  no false "complete" state.
- **Current Truth**: Product design and the setup/OAuth/Extension-state boundary
  remain accepted. Old-baseline Core PR
  [#52](https://github.com/InKCre/core-py/pull/52) and Client PR
  [#68](https://github.com/InKCre/client-web/pull/68) proved the four-step wizard
  and reached a visible setup popup in preview, but they are not mergeable
  upstream truth. Core main has since admitted the hard Client-to-Peer cutover,
  deployment config, capability advertisement and new Source/Cron/Job runtime;
  PR #52 lacks those surfaces. Client main still carries stale generated
  Client-domain projection and PR #68 builds its selector/settings/setup
  transport on `Client.list()` and `rest_api_url`. The local always-available
  Twitter Close correction is valid. The local Client-aware Registry-origin
  correction proved the one-operation snapshot requirement but its authority
  source is obsolete. Both source PRs now require the Peer-native reconstruction
  in D029 before further preview acceptance or merge review.
- **Latest Preview Findings**: Twitter's setup contribution emits the correct
  close event but exposes its Close action only on the final step; the accepted
  correction is an always-available Twitter-owned action, with no Host button
  and no new regression test. Core #52 also freezes the Registry origin from
  process settings. The first local correction read the old current Client, but
  that implementation is now superseded by the admitted Peer baseline:
  `executing Core Peer override > deployment config > process fallback`, with
  one origin snapshot for Release and wheel consumption.
- **Latest Implementation Result**: Sir authorized, reviewed and pushed the
  Peer-native source batch as Core PR #65 and Client PR #71. The accepted
  setup/state/Peer behavior is implemented and both repositories' full local
  and current PR checks are green. Generic Web management reads no longer fetch
  secret-bearing Extension state, and reconfiguration/disconnect disarms
  setup-owned bookmark collection without deleting Source-domain records. The
  latest Impact Handshake removed the unnecessary `register_peer` RPC/D7
  migration in favor of a runtime-field-only Web upsert, and simplified
  Source/Cron/Job setup for the single-user happy path: ordinary Source create,
  explicit Cron create/update, and non-deduplicating run-now. See
  [Peer-native implementation progress](73-peer-native-implementation-progress.md).
- **Latest UX and Protocol Review**: Black-box acceptance reached the Bookmark
  Source step and exposed a connected design defect. The UI conflates choosing
  and creating a Source, exposes unexplained hour/minute fields, uses raw
  controls and hard-coded stepper styling, and passes the nonexistent
  `InkButton.loading` prop instead of `isLoading`. More importantly, the
  Peer-native implementation drifted from the accepted semantic routes to one
  seven-way `action` dispatcher and delegated ordinary Source/Cron/Job work to
  the Twitter Core Distribution. The proposed correction keeps Core Twitter
  OAuth-only, composes ordinary Source/Cron/Job rows directly in the Twitter Web
  target, removes copied Source/Cron IDs and the low-ROI `authorization_id`
  binding from Extension state/job config, and publishes five fixed semantic
  Peer capabilities. See
  [Setup UX and protocol review](74-setup-ux-and-protocol-review.md).
- **UX and Protocol Correction Result**: Sir accepted the connected correction
  and authorized implementation, commit and push. Core Twitter `0.2.1` now
  publishes five fixed OAuth/account capabilities, keeps only OAuth/account
  facts in Extension state, and no longer imports Source/Cron/Job authorities
  from setup. Bookmark collection resolves the current account at execution
  instead of carrying `authorization_id` in Job parameters. Web Twitter `0.2.1`
  now composes ordinary Source/Cron/Job models directly; `@inkcre/core` `0.1.2`
  adds the missing ordinary Cron update operation. Step 3 explicitly separates
  existing Source selection from new Source creation, uses the UI package's
  dropdown/time picker/button happy paths, provides operation-specific loading
  states, and uses application design tokens. Core's pinned full check passed
  with 489 tests/41 skips; after synchronizing with Client main, Web's current
  PR check passed with 140 tests and all workspace/MF builds. Both previews are
  deployed; no merge or public Registry publication followed.
- **Preview Registry Facade Follow-up**: PR acceptance exposed that the current
  Client Pages workflow owns a Twitter-specific static Registry facade. Keeping
  Release and Module Federation bytes on the same Pages origin is an acceptable
  low-cost Client/Extension integration technique; the defect is duplicated
  Registry knowledge in `client-web`, not the hosting origin. The accepted
  direction moves facade construction into the Extension Developer Toolkit
  owned by `ext-reg`. One Toolkit invocation must compose **multiple
  Extensions** into one deterministic static Registry tree, reject Release/path
  collisions, and emit only the native Distribution associations actually
  supplied. A Peer workflow
  may host that tree but must not construct Release descriptors or Registry
  paths itself. Sir delegated the CLI/inventory shape and required both Python
  Simple API and Module Federation in the first version. The chosen direction
  is one explicit language-neutral inventory consumed by `inkcre-ext preview
  build`; Worker and static output share Registry-owned projection functions.
  Each Peer preview delivery owns only its relevant projection: Client Web
  hosts supplied MF associations on its Pages origin, while Core delivery
  publishes a sibling static origin carrying supplied Python
  associations/Simple/wheels from the same exact PR head. Literal Core
  same-origin hosting would deadlock startup restore against its own not-yet
  listening ASGI process and is rejected. The Core sibling is a dedicated
  Cloudflare Pages project deployed and smoked before the Heroku Core preview
  starts; it contains all first-party wheels built by that preview run and is
  retired with the PR preview. No new differential or other test is added. See
  [Multi-Extension static Preview Registry](75-multi-extension-preview-registry.md).
- **Preview Registry Implementation Progress**: Sir accepted the exact delivery
  sequence and explicitly started implementation. `ext-reg` now has the first
  local Toolkit slice: `inkcre-ext preview build` validates one explicit v1
  inventory, accepts multiple Python wheels and Module Federation snapshots,
  derives their native associations from `pyproject.toml` or `package.json`,
  and emits exact Release, PEP 503/658 and MF asset trees. The inventory JSON
  Schema is generated with the existing contracts. No test was added; the
  existing full Registry contract passes with 44 tests, package build and
  Worker dry build. A subsequent unit-boundary review found that this CLI cannot
  ship inside the Registry service distribution: Registry, Host SDK and
  Developer Toolkit are independent product/release units. The local code must
  move into a new `inkcre-extension-toolkit 0.1.0` distribution before release.
  Both Peer repositories consume that release through PDM and `pdm.lock`; Client
  uses root `pyproject.toml`/`pdm.lock` for repository development tooling
  alongside its root pnpm application workspace and does not use uv. See
  [Extension units and Toolkit packaging](76-extension-units-and-toolkit-packaging.md).
- **Preview Workflow Correction and Plan Review**: Sir rejected the proposed
  `Client checks`/Core checks production of deployable SPA, MF, wheel and static
  Registry artifacts. Organization governance keeps required checks as merge
  evidence and gives an isolated preview workflow its own delivery authority.
  The corrected Client and Core preview workflows verify an eligible
  same-repository PR with trusted controller code, check out the exact head,
  build all relevant Peer/Extension outputs, invoke the PDM-locked Toolkit,
  deploy and smoke the result in one run. There is no
  `upload-artifact`/`workflow_run`/`download-artifact` delivery handoff. Fork PRs
  receive no preview credentials; diagnostic failure evidence is not a delivery
  input. Each static facade uses a deterministic PR-scoped Pages branch alias
  known before build, and delivery asserts Wrangler returned that alias. Core
  injects it through `EXTENSION_REGISTRY_URL` before Heroku startup. See
  [Preview delivery authority and readiness review](77-preview-delivery-authority-review.md).
- **Toolkit and Controller Implementation Result**: The local Preview builder
  now lives in an independent `inkcre-extension-toolkit 0.1.0` distribution.
  Registry imports point one way into its base pure library; only the Toolkit
  wheel owns `inkcre-ext`, and its `cli` extra owns HTTP/Typer dependencies so
  they do not enter the Worker runtime. The existing Registry contract passes
  with 44 tests, both distributions build, and the Worker dry build passes.
  Separate Client and Core bootstrap worktrees now carry the default-branch
  controllers plus their repository-wide PDM manifests, inventories/build
  helpers and direct same-run deployment paths. Client's existing full check
  passes; Core workflow/YAML/actionlint/Ruff/Pyrefly checks pass. Neither Peer
  has a `pdm.lock` yet because the Toolkit Release asset does not exist, and no
  lock was forged. The accepted immutable asset is
  `toolkit-v0.1.0/inkcre_extension_toolkit-0.1.0-py3-none-any.whl`; Peer PDM
  dependencies use its `cli` extra. No commit, push, release, merge or remote
  deployment has occurred.
- **Preview Controller Resolution**: Core PR #52 run `31774435213` exposed a
  baseline mismatch, not a controller compatibility requirement. The old PR
  branch lacks the admitted Peer implementation and delivery script while Core
  main owns both. PR #62's legacy-image fallback is rejected. Reconstruct Core
  #52 from current main, port setup to Peer-native contracts, then migrate
  Client #68 to the exact generated Peer contract and capability transport.
- **Delivery Boundary**: Core PR #65 and Client PR #71 are pushed and their
  current checks/previews are green. Client's same-origin read-only facade is
  suitable for Web-only integration, but its implementation ownership is under
  review and Registry production publication is not implied. No public Twitter
  `0.2.1` Release or PR merge is authorized by this packet update.
- **Core Preview Distribution Finding**: PR #65 does not embed first-party
  wheels. Core either reuses an exact Distribution already installed in its
  current dyno or downloads it from the configured Registry exact Release and
  Simple index. The Client facade contained no Python association, production
  Registry now returns 404 for Twitter `0.2.0`, and inspected main publisher
  history did not publish that version. The transient remote source used by the
  earlier successful run is therefore an audit-evidence gap, recorded without
  inventing provenance.
- **Next Step**: With separately authorized Git/release operations, land the
  Toolkit split on ext-reg `main`, publish the independent
  `toolkit-v0.1.0` wheel asset, and replace Registry's bootstrap workspace range
  with that immutable asset before any standalone Registry service release.
  Generate genuine PDM locks in both controller worktrees, rerun their frozen
  checks, then land those bootstrap/controller changes on Client/Core `main`.
  Because `pull_request_target` executes default-branch code, only after that
  may PR #71 and PR #65 update from `main`, drop duplicate preview scaffolding,
  and rerun the same-origin/sibling preview acceptance. Commit, push, release,
  merge and cross-repository mutations remain separately governed operations.

## Supporting Material

- [Working protocol](00-working-protocol.md)
- [Current-system evidence](10-current-system.md)
- [Product-design working model](20-product-design.md)
- [Twitter wizard proposal](21-twitter-wizard.md)
- [Setup authority and protocol proposal](22-setup-authority-and-protocol.md)
- [OAuth callback proposal](23-oauth-callback.md)
- [Extension state proposal](24-extension-state.md)
- [Extension state and setup lifecycle proposal](25-state-and-setup-lifecycle.md)
- [Setup and Host SDK boundary proposal](26-host-sdk-boundary.md)
- [Minimum vertical slice and black-box acceptance proposal](27-vertical-slice-and-acceptance.md)
- [HLD 1 — OAuth callback ingress](31-hld-callback-ingress.md)
- [HLD 2 — Canonical Extension state](32-hld-extension-state.md)
- [HLD 3 — Twitter setup and OAuth protocol](33-hld-twitter-protocol.md)
- [HLD 4 — Web Host contribution and wizard UI](34-hld-web-setup.md)
- [HLD 5 — Versions, repositories and delivery](35-hld-delivery.md)
- [Implementation plan](40-implementation-plan.md)
- [Implementation readiness review](50-readiness-review.md)
- [Implementation result](60-implementation-result.md)
- [Client selector and Client Settings follow-up](70-client-selector-and-settings-follow-up.md)
- [Preview acceptance follow-up](71-preview-acceptance-follow-up.md)
- [Peer-native PR reconstruction](72-peer-native-pr-reconstruction.md)
- [Peer-native implementation progress](73-peer-native-implementation-progress.md)
- [Setup UX and protocol review](74-setup-ux-and-protocol-review.md)
- [Multi-Extension static Preview Registry](75-multi-extension-preview-registry.md)
- [Extension units and Toolkit packaging](76-extension-units-and-toolkit-packaging.md)
- [Preview delivery authority and readiness review](77-preview-delivery-authority-review.md)
- [Decision and question log](30-decisions-and-questions.md)
