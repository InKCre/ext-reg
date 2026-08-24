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

Superseded in part by D030. The first slice reuses a selected bookmark Source or
uses ordinary Source creation. Existing Sources remain independent and
selectable. Finish enqueues one bounded initial Job; rare duplicate Sources or
Jobs are acceptable. No history-mode choice or Source check is added to
uninstall.

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

### D027 — Setup exit remains Extension-owned

Accepted during preview review. The Host popup continues to provide no cancel
or confirm action. Twitter renders one always-available Close action and emits
the existing contribution `close` event. The action is not restricted to the
terminal step, and closing aborts transient wizard work without rolling back
durable setup facts.

### D028 — Registry origin is dynamically Client-overridable — Superseded

The preview diagnosis correctly established the need for an operation-time
override and one origin snapshot, but its Client-specific source was tied to the
obsolete PR baseline. D029 replaces the authority order after the accepted Peer
cutover; no `ClientManager` compatibility path is retained.

### D029 — Rebuild the setup slice on the admitted Peer baseline

Accepted after preview-controller diagnosis. Core PR #52 is not made deployable
by teaching current `main` to accept a legacy Client image. Its old feature
branch is reconstructed from current Core `main`, then the setup capability is
ported semantically onto the current Peer, Extension Host, Source, Cron and Job
contracts. Client PR #68 is subsequently migrated from the technical `Client`
domain to the generated Peer contract and exact capability invocation.

The effective Registry origin for one Host operation is:

1. the executing Peer's non-empty `config.extension_registry_url`;
2. deployment config `extension.registry.extension_registry_url`;
3. the process setting/default.

Each Host snapshots the result once for its native Release/Distribution
operation; Core specifically shares one snapshot across exact Release
resolution and Python Distribution acquisition. The OAuth callback URL comes
from the executing Core Peer's admitted public HTTP base URL. Twitter setup
commands are one Twitter-owned exact Peer capability; the public OAuth callback
remains the only unauthenticated route. No generic setup capability or fixed
Web-to-Core origin is introduced.

### D030 — Browser identity and connection are Peer-native

Accepted for the reconstruction batch. A browser origin generates and persists
one technical Peer UUID, migrating its prior Client UUID when present. Saving
meta configuration must first prove database/JWT connectivity, register that
Peer, save its owner configuration and renew its database-time lease. The
database registration function refreshes runtime-owned name, config schema and
capabilities without overwriting owner-authored config or labels. User-facing
surfaces continue to say “Client” where they describe the product rather than
the technical protocol node.

### D031 — Selected-Client control is Peer topology dispatch

Accepted. The Extensions selector lists Peer rows as product Clients. The
current browser executes its local Web Host lifecycle; a live selected Peer
advertising `core.extension.management.v1` receives an exact capability command;
any other selected Client is still controllable through the atomic durable
desired-state RPC, without an extra label/type restriction. Setup availability
continues to come only from this browser's running Web Distribution.

### D032 — Twitter setup transport is one exact Peer capability

Accepted by the Peer-native reconstruction. Twitter Web discovers live Core
Peers from `core.extension.management.v1` advertisements and invokes
`inkcre.twitter.setup.v1` on the exact selected Core Peer. It does not probe
arbitrary Client/Core origins, use postMessage, or introduce a generic setup
protocol. The public provider callback remains a standalone lifecycle-bound
Core route.

### D033 — Generic management does not project Extension-produced state

Implementation correction. `extensions.state` remains deployment-wide and may
contain credentials inside the accepted authenticated-Peer boundary, but the
generic Extension list/get/mutation protocol has no reason to transport it.
Core management models exclude it and the Web PostgREST adapter explicitly
selects only name, version, enabled Peers, nickname, config and config schema.
Schema stripping after an all-column response is insufficient because the bytes
would already have reached the browser.

### D034 — Authorization reset disarms setup-owned collection

Implementation correction. Replacing the OAuth App with confirmation,
disconnecting the account or reconciling a direct config change invalidates the
bound OAuth account/transactions and disables the setup-owned bookmark Cron.
The Source and Cron remain reusable for reconnect/Finish; this does not inspect
or delete Source-domain records during Extension uninstall and therefore does
not change D012.

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

### D030 — Single-user setup command ROI boundary — Accepted

Do not buy distributed idempotency for low-probability, low-harm duplicate
Source or initial Job creation. The Web wizard disables Source/Finish actions
while their request is pending. Core reuses ordinary Source creation, exposes
clear Cron create/update methods and runs the initial Job through the existing
run-now path. Rare duplicate rows or Jobs remain acceptable and manageable.

### D031 — Browser Peer registration stays in the runtime — Accepted

Do not add an `inkcre.register_peer` database RPC. `WebPeerRuntime` performs an
ordinary `peers` upsert containing only runtime-owned `id`、`name`、
`config_schema` and `capabilities`; omitted owner-authored `config` and `labels`
remain unchanged. Core retains no browser-specific registration protocol.

### D032 — Static Preview Registry construction belongs to the Developer Toolkit — Accepted

A Client Pages preview may host a bounded, read-only Registry facade for
Client/Extension integration. Same-origin hosting is not Registry authority.
The Extension Developer Toolkit owned by `ext-reg`, rather than a Peer
repository, must validate and generate the Release/native Distribution
projection. One Toolkit invocation supports multiple Extensions and composes
one deterministic static tree; it is not a Twitter-specific command repeated
once per plugin. Peers only supply explicit exact-head build inputs, host the
output and test it as consumers.

### D033 — One explicit inventory includes both native Distribution kinds — Accepted

The first `inkcre-ext preview build` slice consumes one explicit,
language-neutral inventory containing multiple Extension Distribution inputs.
It supports both Module Federation snapshots and Python wheels/Simple API in
the first version. The inventory points to producer metadata and build outputs
from the same verified preview checkout rather than duplicating Release
descriptors. Static output covers the
exact Release and native read paths Host SDKs consume; absent inputs produce no
false association.

### D034 — Worker and static preview share executable projections — Accepted

Avoid Registry API drift structurally, not with duplicated fixtures. Extract
Release, Simple HTML/PEP 658, native path and Module Federation materialization
into pure Registry-owned application functions used by both Worker handlers
and the static Preview builder. Peer repositories do not own expected Registry
JSON. Do not add a differential test or any other new test for this follow-up;
reuse the existing Registry checks and Peer preview smoke paths.

### D035 — Each Peer preview delivery owns its native facade — Accepted

Do not put every native Distribution into every preview. `client-web` hosts a
same-origin multi-Extension facade containing the supplied Module Federation
associations. `core-py` delivery publishes a sibling multi-Extension Preview
Registry origin containing the supplied Python associations, Simple pages,
wheels and metadata built from the same exact PR head. It is not served by
the Core ASGI process because startup restore must acquire wheels before that
process accepts requests. Each exact Release descriptor exposes only
associations backed by bytes on its Registry origin. The shared Toolkit supports
both formats; the per-Peer inventory selects the projection. Hosting does not
transfer Registry authority to the Peer.

### D036 — Core's sibling Preview Registry is Cloudflare Pages — Accepted

Deploy Core's Toolkit-generated static Python facade to a dedicated Cloudflare
Pages project, not Heroku, a Worker/D1/R2 preview, the Client Pages project or
the ext-reg UI-preview project. The Core PR workflow builds all first-party
wheels, deploys and smokes its exact-head static tree first, then configures the
Heroku Core preview to use that stable PR alias before application startup. PR
cleanup retires the Pages branch with the other preview resources.

### D037 — Peer workflows consume a released, locked Developer SDK — Superseded

Do not pin an ext-reg Git commit or moving branch in Client/Core workflow YAML.
The lockfile direction remains accepted, but publishing the CLI in a normal
`inkcre-extension-registry` release and using uv in Client were rejected by the
subsequent unit-boundary review. D038 replaces those details.

### D038 — Registry, Host SDK and Developer Toolkit are separate units — Accepted

Publish `inkcre-ext preview build` in an independently versioned
`inkcre-extension-toolkit` distribution, initially `0.1.0`. The Registry
service distribution does not expose this developer CLI; Host SDKs do not
depend on it at runtime. Registry service code may depend one way on the
Toolkit's pure artifact inspection/projection library to prevent drift. Both
Core and Client consume the released Toolkit through PDM plus `pdm.lock`.
Client keeps pnpm for its application but owns one PDM tooling project;
there is no technical limitation requiring uv, so uv is rejected.

### D039 — Client's PDM development-tool project lives at repository root — Accepted

Client may be a polyglot repository: root pnpm continues to own application and
Extension JavaScript dependencies, while root PDM owns Python development tools
only. Use root `pyproject.toml` and `pdm.lock`, which is PDM's normal happy path.
Do not recreate the deleted historical `tooling/extension-publisher` directory.
An `extensions/` PDM project would work technically, but the Toolkit lock serves
repository-wide multi-Extension preview/CD and therefore belongs at the root.

### D040 — Preview delivery builds and deploys its own exact-head output — Accepted

Do not make `Client checks`, Core checks, or any other pull-request validation
job the producer of deployable Preview Registry, SPA, Module Federation, wheel,
or Pages artifacts. In particular, do not use an `upload-artifact` /
`workflow_run` / `download-artifact` handoff from checks into preview delivery.

The repository-owned preview workflow is one delivery authority. It verifies an
eligible same-repository pull request with a trusted controller, checks out the
exact pull-request head, installs the repository's frozen toolchains, builds the
Peer application and relevant Extension Distributions, runs `inkcre-ext preview
build`, deploys that output, and smoke-checks the deployed preview in the same
workflow run. Required checks remain independent merge evidence; they may build
for validation or upload diagnostic failure evidence, but their outputs are not
delivery inputs. Fork pull requests receive no preview credentials and follow
the organization-level maintainer-approval behavior for secret-free Actions.

The Toolkit needs its public origin before Pages deployment, so each workflow
uses a deterministic, PR-scoped Pages branch alias as `--public-origin`. The
delivery step must assert that Wrangler reports the expected alias. Core passes
that same alias as `EXTENSION_REGISTRY_URL` before starting its Heroku preview.
Do not claim a random deployment URL as the embedded origin after the static
tree has already been built.

### D041 — Python activation is local-first and owned by a Host Runtime unit — Accepted

Deployment `installed`, Core-Peer-local Python Distribution `present`, and
runtime `running` are distinct states. Core enable/cold restore must inspect and
validate the exact locally installed Distribution before any Registry I/O. An
exact local hit activates without Release refresh, yank lookup or Simple access;
only a local miss enters Registry resolution and pip acquisition. Disable does
not remove local presence. A rebuilt ephemeral Peer may legitimately require
Registry acquisition again.

This policy belongs to an independently versioned, Core-specific Python
Extension Host Runtime release unit in `ext-reg`, not the Registry service,
Developer Toolkit, Core database or Peer protocol. Core depends on that Runtime
for Release resolution, native acquisition and module load/unload. Core itself
retains `ExtensionBase` lifecycle, RuntimeClaim and publication; the Runtime
imports no Core tables, transports or adapters. Long-term discovery uses a versioned installed metadata
record carried by the wheel and derived from `[tool.inkcre-extension]`, standard
wheel metadata and entry points. Toolkit generation/admission, Registry Python
admission and Runtime local discovery share that pure identity model. Core must
remove its duplicate native consumer after adopting the released Runtime.

### D042 — ext-reg owns the per-tech-stack/per-Peer-type Host Runtime family — Accepted

Extension Registry, Extension Developer Toolkit and Extension Host Runtime are
three first-class product unit families managed in `ext-reg`. Host Runtime is a
family rather than one universal implementation: Core Python and Client Web
each consume an independently released Runtime tied to their Host SDK,
technology stack, native Distribution consumer and lifecycle model. Their
currently embedded Runtime implementations are ownership debt to extract and
then delete from the Peer repositories.

Shared truth is limited to language-neutral Release/native association models
and the product distinction between deployment `installed`, local/session
`present`, and runtime `running`. An `extensions` row means the Release is
installed in the deployment while allowing lazy native acquisition by each
Peer. `present` is always derived by the native consumer and is never persisted
to the shared database. Wheel-installed Extension metadata is required; its
schema/file name and Runtime package/API names are delegated implementation
decisions, not unresolved product questions.

### D043 — Host SDK/Runtime packaging and integration seam — Accepted

The **Extension Host SDK** is a conceptual name for the API seen and imported by an Extension for one
Peer type. It includes lifecycle base/types, config/state access and
Peer-specific contribution APIs. It is not a second distribution, package,
manager or deployment service: Extension and Peer use the same per-Peer-type
Host Runtime package/implementation. Its compatibility identity remains the Host
SDK/Peer identity (`core-py`, `@inkcre/core`, and their versions), because an
Extension may also use admitted Peer APIs directly.

The **Extension Host Runtime** is that same unit's Host-side implementation that discovers,
acquires, loads and manages Extensions. It owns `ExtensionManager`, the
implementation and lifecycle binding of `ExtensionBase`, native Distribution
consumption, running-instance/resource ownership and lifecycle compensation.
No detached-Extension development use case justifies a separate SDK artifact or
formal SDK/Host export split now.

Core remains authoritative for the `extensions` SQL schema, migrations and
database concurrency. A Repository is not required. The earlier proposal only
followed from an unnecessary rule that Runtime could not depend on its Peer
implementation. Restore the established Active Record/充血模型 direction:
Core's `ExtensionModel` owns the schema and persistence behavior for the whole
record (install/version/enabled/config/state/config-schema); the Core-specific
Runtime's `ExtensionManager` consumes that model API directly, and
Runtime-owned `ExtensionBase` binds the active model so config/state methods use
the same authority. The lower Core model layer must not import Runtime, keeping
the module graph acyclic. Do not add a Repository, reusable
"Persistence Port" framework or "Contribution Port": each
per-Peer-type Runtime integrates with that Peer type's existing concrete
FastAPI/Source/Resolver/Peer or Module Federation mechanisms. Client retains
database/UI and remote-Peer delegation. This direction supersedes the narrower
D041 planning detail that left `ExtensionBase` lifecycle and the entire manager
in Core. The product and architecture decision is accepted; the revised package
dependency map remains an implementation-planning deliverable rather than an
open product decision.

The preferred mature contract toolchain is: FastAPI/Pydantic remains the
Registry contract source and emits OpenAPI 3.1/JSON Schema; Python consumers are
generated with `datamodel-code-generator`; Web types, fetch SDK and Zod v4
response schemas are generated by `@hey-api/openapi-ts` with its fetch and Zod
plugins. CI regenerates and fails on a dirty diff. Do not maintain parallel
handwritten Zod Release models or weaken the accepted Web generation path to a
types-only fallback during implementation.

### Q010 — What is the minimum production-shaped vertical slice? — Resolved

[Minimum Vertical Slice and Black-box Acceptance Proposal](27-vertical-slice-and-acceptance.md).
The slice must prove real Extension usefulness—durable OAuth, Source creation,
first bookmark collection, restart/Peer handoff and recovery—not merely render
the stepper. Black-box proof is deferred; implementation PRs retain focused
repository checks but do not invent a substitute provider harness.

## Queued Questions

No product question is queued. D041/D042 freeze Python local-first activation
and repository ownership of the Runtime family; accepted D043 now aligns SDK/Runtime
terminology and moves `ExtensionManager` plus `ExtensionBase` implementation
into Runtime while preserving Core's Active Record authority without a new
Repository. The previous extraction plan/readiness verdict is therefore
superseded and must be mechanically revised and re-reviewed before source work.
