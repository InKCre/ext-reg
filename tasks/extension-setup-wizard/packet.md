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
- **Current Truth**: Product design, HLD and authorized local implementation are
  complete. The Core branch now carries contract v3, deployment-wide
  `extensions.state`, typed Host config/state operations, exact public callback
  lifecycle, Authlib Twitter OAuth, Bookmark Source/Finish behavior and Twitter
  Python `0.2.0`. The Client branch now carries Web Host setup contribution,
  popup teardown, abort-safe Peer requests, the four-step Twitter wizard, synced
  v3 generated contract, `@inkcre/core` `0.1.1` and Twitter Web `0.2.0`. Core's
  full contract is green with 241 tests; Client's full contract is green with 88
  tests and all builds. Client contract sync/check passed against a task-built
  final Core image through the configured SSH Docker provider. The public
  Registry still returns `404` for `inkcre/twitter@0.2.0`. The task-owned runtime,
  tunnel, volume, generated contract staging files and read-only probe output
  were removed. The reviewed changes are committed and pushed in Draft Core
  [PR #52](https://github.com/InKCre/core-py/pull/52), dependent Client
  [PR #68](https://github.com/InKCre/client-web/pull/68), and this packet's
  [ext-reg PR #13](https://github.com/InKCre/ext-reg/pull/13). Nothing was
  published, deployed or merged. Client #68 exposed a workflow-topology defect:
  its intentional v3/stable-v2 Database contract failure also prevented the
  otherwise-valid Web artifact and PR preview. Independent Client
  [PR #69](https://github.com/InKCre/client-web/pull/69) splits `Database
  contract` from `Workspace contract`; the trusted preview controller will
  accept only a successful same-run Workspace job and exact live artifact,
  while merge and production delivery retain the stronger full-check gates.
- **Delivery Boundary**: Black-box acceptance is deferred to Sir. Eventual
  implementation in this task stops when relevant PRs are ready for review; no
  merge, Release publication, deployment or black-box run is implied.
- **Next Step**: Admit workflow PR #69 first and add `Database contract` to
  Client `main` branch protection; then sync Client #68 with `main` so its
  Workspace artifact can deploy a preview even while its Database check remains
  merge-blocking. Client still needs Core admission and an exact admitted-
  contract refresh before merge. Black-box provider acceptance remains
  explicitly deferred to Sir; it is not silently converted into a local mock.

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
- [Decision and question log](30-decisions-and-questions.md)
