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
- **Latest Implementation Result**: Sir authorized the Peer-native source batch.
  Core and Client now have uncommitted reconstruction worktrees; the accepted
  setup/state/Peer behavior is implemented and both repositories' full local
  checks are green. Generic Web management reads no longer fetch secret-bearing
  Extension state, and reconfiguration/disconnect disarms setup-owned bookmark
  collection without deleting Source-domain records. Exact Client
  generated-contract sync still requires an exact Core feature image because
  the pinned generator needs an unavailable container runtime; this remains the
  declared dependent-PR admission gate. The latest Impact Handshake removed the
  unnecessary `register_peer` RPC/D7 migration in favor of a runtime-field-only
  Web upsert, and simplified Source/Cron/Job setup for the single-user happy path:
  ordinary Source create, explicit Cron create/update, and non-deduplicating
  run-now. See
  [Peer-native implementation progress](73-peer-native-implementation-progress.md).
- **Preview Controller Resolution**: Core PR #52 run `31774435213` exposed a
  baseline mismatch, not a controller compatibility requirement. The old PR
  branch lacks the admitted Peer implementation and delivery script while Core
  main owns both. PR #62's legacy-image fallback is rejected. Reconstruct Core
  #52 from current main, port setup to Peer-native contracts, then migrate
  Client #68 to the exact generated Peer contract and capability transport.
- **Delivery Boundary**: Previous preview evidence remains useful but no longer
  proves merge readiness. Black-box acceptance is paused until Peer-native Core
  #52 and dependent Client #68 pass their exact contracts and previews. No
  public Twitter Release, production delivery, PR merge or PR #62 closure is
  implied.
- **Next Step**: Under separate commit/push authority, create the exact Core
  feature image, sync the Client generated truth, remove the narrow temporary
  type seam and rerun the already-green Client contract before merge. Commit,
  force-with-lease push, ordinary push, PR closure and preview delivery remain
  separately authorized operations.

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
- [Decision and question log](30-decisions-and-questions.md)
