# Decision and Question Log

## Accepted Inputs

### I001 — Task identity

The new task is named **Extension Setup Wizard**.

### I002 — First vertical slice

Use Twitter as the design and acceptance example. The motivating useful outcome
is collecting Twitter bookmarks, and OAuth login is at least one required setup
step.

### I003 — Presentation Peer

The guided experience should be available in `client-web`.

### D001 — Whole-Extension scope

Accepted. The wizard sets up the Extension as a whole, not only bookmark
collection. For Twitter, working bookmark collection is the initial concrete
proof of the Extension's minimum useful baseline.

### D002 — Entry and availability

Accepted. The setup entry is on the Extension card in the `client-web`
Extensions page and becomes available once at least this Web Peer has enabled
and loaded the Extension. This does not imply that any Core Peer is enabled and
does not scope setup to this Web Peer; setup is deployment-wide.

### D003 — Interaction form

Accepted. Setup opens in a popup and uses an ordered, multi-step installer-like
flow that guides the user one step at a time.

### D004 — Truth-derived completion

Accepted. Setup progress and completion come from durable, observable domain
facts. A one-time OAuth callback or a manually stored completion boolean is not
sufficient.

### D005 — Popup versus stepper ownership

Accepted. `client-web` owns only the popup container. The Extension's Web
Distribution owns the stepper and everything inside the popup, including its
navigation and step state.

### D006 — User-configured OAuth App

Accepted. The wizard guides the user through registering the X developer App
and entering Client ID and Client Secret. These configure the deployment-wide
Twitter Extension.

### D007 — Extension config security boundary

Accepted correction. Canonical deployment-wide `extensions.config` may contain
Secrets; authenticated Peers are inside InKCre's chosen access boundary. Do not
introduce a second Core-only Extension secret store.

### D008 — No callback-to-Web browser coupling

Accepted. The Core OAuth callback must not depend on the `client-web` origin,
opener relationship or a `postMessage` contract, even if removing that coupling
costs some automatic-return UX.

### D009 — Decoupled OAuth observation

Accepted. The Core callback renders a standalone result and never communicates
with the Web page. The Twitter Web Distribution polls a short-lived transaction
through the ordinary Twitter Core API and reloads the setup projection after a
terminal result.

### D010 — Deployment-wide Extension state

Accepted in principle. Setup introduces a real general Extension-state need:
Extension-produced durable facts such as Twitter account credentials and OAuth
transactions must survive restart and Peer handoff without being mislabeled as
user config or Source state. Reuse the canonical Extension installation row
rather than adding a second one-to-one state table; review the exact model in
[Extension State Proposal](24-extension-state.md).

### D011 — Extension-state concurrency authority

Accepted correction. The Extension Host SDK is a typed access interface, not
the concurrency authority. Core's shared state authority owns persistence and
cross-Peer serialization, backed by database transactions and constraints. The
Extension and Host SDK do not implement distributed locking.

### D012 — Uninstall does not inspect Sources

Accepted correction. Uninstall deletes the canonical Extension record and its
config/state directly. It neither checks nor deletes Sources. The Source domain
owns behavior for records whose type becomes unreachable.

### D013 — Host SDK setup boundary

Accepted. The Web Host SDK contributes and mounts an optional setup component;
the Core Host SDK provides typed Extension-state access while delegating to
Core's authority. Twitter's Web/Core Distributions own the entire setup
projection and protocol. No generic setup or OAuth engine is introduced.

### D014 — Delivery stops at PR review

Accepted. Black-box acceptance is deferred to Sir. This task's eventual source
delivery ends with relevant PRs ready for review; it does not merge, publish,
deploy or perform black-box acceptance without separate authorization.

### D015 — Canonical state authority

Implementation baseline. Add `extensions.state JSONB NOT NULL DEFAULT '{}'`;
Core/PostgreSQL owns row-lock transactions and direct-write restrictions.
Extension code receives typed inherited operations, not SQL rows/sessions. The
misnamed installed-row `ExtensionState` types are renamed to
`InstalledExtension`/`ExtensionStore`.

### D016 — Exact public callback contribution

Implementation baseline. A running Extension may claim an exact method/path
that it actually published. JWT bypass exists only while that claim is active
and is withdrawn with the runtime publication. Twitter claims only
`GET /twitter/auth/callback`.

### D017 — Twitter OAuth library and state machine

Implementation baseline. Use Authlib `AsyncOAuth2Client` with HTTPX, PKCE S256,
confidential-client Basic token authentication, read/offline scopes and a
durable transaction/account state machine. A temporary executable probe proved
the chosen library path and frozen dependency resolution. Callback exchange is
claimed once by `pending -> exchanging`; it is not lease-reclaimable because a
crashed process cannot know whether X consumed the one-use code.

### D018 — Source and Finish semantics

Implementation baseline. The first slice reuses an existing bookmark Source or
asks Core's Source authority to ensure at least one exists under serialization.
This does not impose a one-Source-per-type invariant: existing Sources remain
independent and selectable. Finish creates/reuses one initial bounded job. No
history-mode choice or Source check is added to uninstall.

### D019 — Host and Extension versions

Implementation baseline. Core Python and `@inkcre/core` advance to `0.1.1`;
both Twitter native Distributions advance together to Extension Release
`0.2.0` and require Host SDK `>=0.1.1 <0.2.0`. Existing Extension ranges remain
compatible.

### D020 — Cross-repository delivery

Implementation baseline. Prepare one Core PR and one dependent Client PR. Use
the configured SSH Docker provider to generate Client contract v3 from the exact
unmerged Core branch image. No ext-reg source PR, merge, publication, deployment
or black-box run belongs to this task.

### D021 — Cross-Peer config/state freshness

Implementation baseline after independent plan review. `ExtensionBase.config`
remains a compatibility snapshot, not shared authority. Freshness-sensitive
Twitter setup, OAuth, refresh and provider operations read validated current
config/state from Core before use. Official OAuth uses a fresh Authlib client per
bounded provider operation rather than a cross-operation singleton; only the
expert Twikit path may retain a config-bound local cache. No process-to-process
invalidation channel is introduced.

### D022 — Review-ready cross-repository handoff

Implementation baseline after independent plan review. The Client PR may be
reviewed using generated evidence from the exact unmerged Core branch image,
but remains Draft and explicitly merge-blocked on the Core PR. Its GitHub checks
continue to select protected stable Core and may remain dependency-blocked until
Core lands; no feature-image CI bypass is added. Generated contract and checks
must then be refreshed against the admitted Core revision before Client merge.
Review readiness is not false upstream admission.

### D023 — One current OAuth flow

Implementation baseline after sequence review. Beginning a new OAuth flow
atomically supersedes every older non-terminal flow for the same App. An older
callback may finish its external request but its conditional durable commit must
fail, so callback ordering cannot overwrite the user's newer choice.

### D024 — Readiness belongs to the current authorization

Implementation baseline after sequence review. A connected account records
an opaque `authorization_id`; only a non-failed collection job explicitly bound
to that ID can satisfy setup readiness. Reconnecting replaces the ID, and a
Finish/reconnect race cannot attribute an old authorization's job to the new
account.

### D025 — Config writes are not lifecycle teardown

Implementation baseline after multi-Peer review. Explicit Host/Extension config
operations persist immediately through Core authority and then update the local
snapshot. Base `on_close()` does not write config. A Peer disabling with an old
startup snapshot therefore cannot roll back a newer config committed elsewhere.

### D026 — MVP state/version gate

Implementation baseline after feasibility review. Without a declared migration
contract, Core cannot prove a different Distribution version understands
non-empty state without executing future bytes. Same-version install is
idempotent; a version change is allowed only while canonical state is `{}` and
otherwise fails before mutation. The initial Twitter `0.1.1 -> 0.2.0` cut remains
valid because the new column starts empty.

## Resolved Product Questions

### Q001 — What does “Twitter setup complete” mean? — Resolved

Use the Extension-wide minimum baseline in
[Product-design Working Model](20-product-design.md), ending in durable account
authorization, required initial resources including an eligible bookmark Source,
and a bounded Extension readiness check.

Why this is the first question: screen structure, setup APIs, persistence, and
the relationship to enablement all depend on the terminal condition. Current
OAuth state is memory-only, so accepting “OAuth callback returned success” as
completion would create a misleading UX.

### Q002 — Who owns the popup shell and Extension-specific content? — Resolved

`client-web` owns only the popup container. The enabled Web Distribution owns
the complete setup UI and completion projection. The Extension Host SDK exposes
only the contribution boundary between them.

### Q003 — What is the minimum Web Extension API contribution?

Accepted. Add one optional setup Vue component to the Web
Extension module. The Host mounts it inside the popup and accepts a close
request. Do not add a generic step schema, Host-owned stepper, progress state, or
`setup_complete` callback.

### Q004 — What is the Twitter first-release wizard? — Resolved

Accept the four-step flow and first-release boundary in
[Twitter Wizard Proposal](21-twitter-wizard.md): Prepare, Connect account,
Bookmark collection, Review and start. Guide user-owned X App registration and
credential submission; request only read/offline scopes; support official X
OAuth only; reuse or create a Source; finish when readiness passes and Core
accepts the first collection job.

### Q005 — Where do setup facts and commands live? — Resolved

Use canonical `extensions.config` for user-declared OAuth App settings and
canonical `extensions.state` for Extension-produced account credentials and
OAuth transactions under the same accepted authenticated-Peer boundary. Keep
Source facts in the Source domain. Twitter exposes one validated setup
projection and Twitter-specific semantic commands; no credential is Peer-scoped
and no generic OAuth framework or second secret store is introduced.

### Q006 — How does OAuth return to the wizard? — Resolved

[OAuth Callback Proposal](23-oauth-callback.md) is accepted. The Twitter Core
callback completes the exchange and atomically updates account and transaction
state, but never communicates with the Web page. The Twitter wizard
independently polls that transaction through its Core API and reloads
authoritative setup facts. Reopening always resumes from durable deployment
facts.

### Q007 — What is the minimum Extension state model? — Resolved

[Extension State Proposal](24-extension-state.md) is accepted with D011's
authority correction. Add `extensions.state` as one
deployment-wide JSON object, validate and mutate it through the Core Host SDK,
and keep raw table/model details out of Extension code. Config is user-declared;
state is Extension-produced; both may contain Secrets inside the accepted trust
boundary. The Host SDK delegates writes to Core's concurrency authority.

### Q008 — How do setup and state behave across lifecycle operations? — Resolved

[Extension State and Setup Lifecycle Proposal](25-state-and-setup-lifecycle.md)
is accepted with D012's uninstall correction.
Reconfiguration invalidates only authorization bound to replaced OAuth App
credentials; reconnect failure preserves a working account; Peer disable keeps
deployment state; MVP upgrade/rollback rejects incompatible state instead of
inventing migrations; uninstall removes Extension config/state without
inspecting Sources.

### Q009 — Which setup concepts belong in Host SDKs? — Resolved

[Setup and Host SDK Boundary Proposal](26-host-sdk-boundary.md). The Web Host SDK
only contributes and mounts an optional setup component. The Core Host SDK only
adds typed access to deployment-wide Extension state and delegates persistence
to Core's authority. The wizard, projection, OAuth transaction protocol, Source
composition and readiness commands remain jointly owned by Twitter's Web and
Core Distributions.

### D027 — Selected-Client enablement control — Accepted

Restore the Extensions-page Client selector as an application-level management
surface. The card switch projects the selected Client's membership in the
canonical `extensions.enabled[]`: this browser Client is controlled through the
local Web Host SDK; an addressable remote Client is controlled through its
generic Host enable/disable API; an unaddressable remote Client is controlled
as durable desired state through the existing atomic state-port RPC. This
desired-state path applies to every unaddressable Client without an additional
type/label restriction. Its running process cannot be synchronously stopped,
and the UI must say that the change is realized on its next restore/reload. No
direct `enabled[]` edit is allowed.

### D028 — Setup availability is not selector state — Accepted

The selected Client controls only enablement. Whole-Extension setup remains a
contribution of the currently running Web Distribution. Selecting Core or any
other Client must not hide a setup contribution already loaded by this browser.

### D029 — Restore all-Client Settings management — Accepted

Restore the existing Client list in Settings beneath a separate all-deployment
Clients section. This follow-up manages existing Client metadata, REST API URL,
health and declared config; it does not introduce manual Client creation or
deletion.

### Q010 — What is the minimum production-shaped vertical slice? — Resolved

[Minimum Vertical Slice and Black-box Acceptance Proposal](27-vertical-slice-and-acceptance.md).
The slice must prove real Extension usefulness—durable OAuth, Source creation,
first bookmark collection, restart/Peer handoff and recovery—not merely render
the stepper. Black-box proof is deferred; implementation PRs retain focused
repository checks but do not invent a substitute provider harness.

## Queued Questions

No product, HLD, dependency, environment or repository-sequencing question is
queued. The independently corrected implementation proposal is ready for Sir's
review; source implementation remains unauthorized until a later explicit
start.
