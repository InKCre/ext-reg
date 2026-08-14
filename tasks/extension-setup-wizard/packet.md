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
  full contract is green; Client's full contract is green with 90 tests and all
  builds. Client contract sync/check passed against a task-built
  final Core image through the configured SSH Docker provider. The public
  Registry still returns `404` for `inkcre/twitter@0.2.0`. The task-owned runtime,
  tunnel, volume, generated contract staging files and read-only probe output
  were removed. The reviewed changes are committed and pushed in Draft Core
  [PR #52](https://github.com/InKCre/core-py/pull/52), dependent Client
  [PR #68](https://github.com/InKCre/client-web/pull/68), and this packet's
  [ext-reg PR #13](https://github.com/InKCre/ext-reg/pull/13). Preview-controller
  Client [PR #69](https://github.com/InKCre/client-web/pull/69) and Core
  [PR #53](https://github.com/InKCre/core-py/pull/53) were admitted. Their
  resulting topology gives Client #68 an exact checked-artifact Pages preview
  and Core #52 isolated Core/PostgREST preview apps. The preview database is
  seeded with enabled `inkcre/twitter@0.2.0`; a cold browser load restores the
  Twitter Remote, renders `Set Up`, and opens the four-step `Set Up Twitter`
  dialog. Client commit `f25e684` fixed the discovered startup/list ordering
  race. The independent v3/stable-v2 `Database contract` failure remains a
  deliberate merge blocker but no longer blocks Preview deployment. Continued
  acceptance exposed two older Client regressions: the Extensions page no
  longer selects and controls a specific Client, and Settings no longer renders
  its existing all-Client management list. The current acceptance database
  reports an Extension enabled on one Client; the UI does not identify it, and
  the current Web Client was previously enabled during acceptance, so it must
  not be assumed to be Core. The authorized follow-up implementation is now
  complete locally: Client selection and three-path enablement dispatch are
  restored, setup remains current-Web-runtime scoped, and Settings again manages
  all registered Clients. The final full repository gate is green.
- **Delivery Boundary**: The bounded black-box gate through visible Setup Wizard
  entry is complete. Provider OAuth acceptance is paused while the Client
  selector and all-Client settings regression are reviewed. Core #52 and Client
  #68 remain unmerged; no public Twitter Release or production delivery is
  implied by the preview.
- **Next Step**: Review the completed
  [Client selector and Client Settings follow-up](70-client-selector-and-settings-follow-up.md).
  Commit/push and preview delivery still require separate authorization. After
  this follow-up and provider review, admit Core #52 before refreshing Client #68's generated
  database contract; only then can the independent Database contract gate
  become green and Client admission proceed.

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
- [Decision and question log](30-decisions-and-questions.md)
