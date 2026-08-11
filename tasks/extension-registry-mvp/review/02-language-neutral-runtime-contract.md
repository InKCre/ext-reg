# Review Batch 02 — Language-neutral Runtime Contract

## Review Question

How is language-neutral Extension API compatibility checked before executable
Distribution bytes are acquired, while format-native resolution is delegated to
Python packaging or a Module Federation Host?

## Responsibility Boundary

Distribution installability is delegated, but not every responsibility is:

```text
Registry
  owns Extension Name, Release, publication and native Distribution endpoints

native consumer (Python packaging / MF Host)
  resolves format-native metadata, environment constraints and dependencies
  before acquiring executable Distribution bytes

Extension Runtime Adapter
  orchestrates preflight/acquisition, enforces the InKCre Extension API contract,
  runs lifecycle, and updates enabled state
```

The compatibility model remains one-directional: a Distribution exposes a
pre-download Distribution Descriptor; a consumer evaluates its Distribution
Compatibility Contract against the real environment before acquiring executable
bytes.
There is no producer-capabilities/consumer-requirements pair.

## Current Custom Compatibility Keys

The implemented generic target contract contains exactly eight keys:

| Current key | Meaning | Revised owner |
| --- | --- | --- |
| `inkcre.integration` | Generic artifact/integration format | Retire; Distribution Format and native Registry endpoint |
| `inkcre.extension-api` | Compatible InKCre Extension API range | Preserve semantically; encode through language-native Extension API SDK dependency/handshake |
| `module-federation.runtime` | MF runtime version | MF Distribution metadata and Host |
| `module-federation.share-scope` | Required MF share scope | MF Distribution metadata and Host |
| `shared.vue` | Shared Vue version range | MF shared dependency metadata and Host |
| `shared.@inkcre/core` | Shared whole client Core version | Retire; replace with the narrow `@inkcre/extension-api` SDK contract |
| `web.ecmascript` | Emitted JavaScript execution baseline | Web build metadata/browser runtime; not a cross-format Registry key |
| `python` | Python interpreter compatibility | `Requires-Python` and wheel compatibility tags |

There is no remaining open-ended Registry “capabilities” vocabulary after this
translation. New ecosystem constraints belong to their Distribution Format.

## Compatibility Term

The complete pre-download concept remains the **Distribution Compatibility
Contract**, but the Host SDK's Extension API Profile contains the applicable
Distribution semantics:

```text
Extension API Profile
  owns accepted Distribution protocol/format and metadata semantics
  owns Extension entry, lifecycle, and Core API compatibility

Distribution Compatibility Contract
  is the profile-specific pre-download metadata evaluated by that Host SDK
```

Its concrete pre-download representation is a **Distribution Descriptor**. The
Descriptor can be format-native instead of one generic manifest:

- Python Simple API response, wheel filename/tags, and separately served Core
  Metadata;
- Module Federation `mf-manifest.json` and shared dependency metadata.

## Extension Host API Compatibility — Before Download

The previous proposal assumed one language-neutral Extension API SemVer line
implemented by Python and Web bindings. That incorrectly coupled unlike hosts:
`core-py` and `client-web` do not offer the same contribution points, lifecycle,
resource model, or loading semantics.

The narrower model is an **Extension API Profile**. A profile belongs to a Host
SDK/Peer family and defines that family's Distribution consumption contract,
Extension entry shape, lifecycle, Peer implementation surface available to the
Extension, and configuration semantics. It is a compatibility concept, not
necessarily a standalone SDK package or restricted public API surface.

The previous text incorrectly described Distribution Format and API Profile as
parallel product axes. The actual containment is:

```text
Extension API Profile
  -> Host SDK implementation
     -> Distribution Consumer (pip/Python packaging or MF Host)
     -> accepted Distribution format and native metadata
  -> Extension entry and lifecycle
  -> compatible Peer implementation surface
```

Format remains a concrete Registry/storage/protocol fact, but the deployment
does not evaluate it as an independent generic compatibility condition. The Host
SDK already knows which native Registry endpoint, metadata, and Distribution
formats its API Profile supports.

A Distribution declares Host API compatibility through its format-native
metadata, and the Registry exposes it before executable bytes:

- a Core Python Distribution currently imports `core-py`'s `app.*` and `libs.*`
  modules directly; there is no installable Core Extension API dependency to
  express this compatibility through standard `Requires-Dist` today;
- a Client Web MF Remote directly depends on the real `@inkcre/core` package and
  declares shared/dependency compatibility in its Module Federation/package
  metadata, but that package is the Client Core rather than a separately carved
  Extension API;
- only after the Host SDK confirms both format compatibility and its own Host
  API profile/range does the Distribution Consumer acquire/load executable
  bytes.

The Registry validates on publication that the pre-download Descriptor agrees
with the Distribution's native metadata and declares a supported Extension API
SDK. It does not select compatibility for the Peer.

Any post-download entry-shape assertion is conformance defense against a broken
or malicious Distribution. It must not be the first point at which Extension
API incompatibility is discovered and is not part of compatibility selection.

## Current Lifecycle Shape

The Registry Runtime packages currently define four language-neutral hooks:

```text
initialize -> activate -> deactivate -> dispose
```

- Web exposes these optional hooks through `ExtensionModule` and executes them
  with `ExtensionLifecycleController`.
- The Registry Python package exposes the same four-hook Protocol and lifecycle
  state machine.
- `core-py` does not yet implement that API directly: its Extension classes use
  `on_start/on_close`, `_init_sources`, `_init_resolvers`, and
  `_register_apis`. This is a concrete divergence requiring an adapter or API
  migration, not evidence that the APIs are already unified.

## Current Responsibility Audit

The concern that the Runtime is too thin is **confirmed** by implementation
evidence:

- the shared Python and Web Runtime packages own contract models, Registry HTTP
  helpers, generic compatibility matching, and a context-free four-hook
  lifecycle executor;
- `client-web`'s `RegistryExtensionManager` owns installation calls, Peer
  identity, Registry resolution, target selection, artifact-manifest fetch,
  Module Federation registration/loading, enabled-state persistence, startup,
  shutdown, serialization, and failure compensation around persistence;
- `core-py`'s `RegistryExtensionManager` additionally owns embedded-artifact
  admission, ZIP/module loading, runtime claims, configuration persistence,
  contribution publication/withdrawal, and startup recovery;
- the current Extension API supplies no Runtime context. Python Extensions
  mutate Source/Resolver/FastAPI registries through class methods, while the Web
  Twitter Extension registers its resolver as a module-import side effect.

The architectural problem is not merely that the adapters contain many lines.
The adapters own the operation policy, while the Runtime is passed a loader and
can only execute hooks. That makes lifecycle, rollback, contribution ownership,
and enabled-state consistency diverge by Peer.

## Accepted Responsibility Direction

The top-level integration product is better described as an **Extension Host
SDK**, not as a standalone Extension Runtime plus a dominant Adapter:

```text
Peer
  -> exposes its Core API directly to Extensions
  -> embeds a platform-specific Extension Host SDK
       -> Distribution Consumer
       -> Extension manager and lifecycle driver
       -> small deployment-state port implemented by the Peer

Extension Distribution
  -> is acquired/loaded by the Host SDK
  -> implements that SDK's Extension API Profile
  -> calls the Peer/Core API directly
```

The Peer owns its process, product capabilities, persistence, and startup
topology. The Host SDK owns Extension execution semantics inside that host. The
Runtime remains a real component, but it is an internal engine of the Host SDK
rather than the top-level product topology.

This **Extension Host SDK** is also distinct from the **Extension Developer
SDK**. The former is embedded by Peer developers at software runtime; the
latter is used by Extension developers for authoring, local testing, building,
conformance, and publication.

For an enable, cold start, disable, or shutdown operation the Host SDK owns its
platform-specific sequence and failure semantics:

```text
read installed Release and enabled intent through a semantic state port
  -> obtain and preflight a Distribution Descriptor
  -> use the Host SDK's Distribution Consumer to acquire/load bytes
  -> validate the Extension entry
  -> invoke that API Profile's lifecycle
  -> persist enabled through the state port only after success
  -> invoke profile-specific close/rollback behavior on failure
```

Each platform/technology-stack Runtime implementation owns its Distribution
consumption mechanism:

- a Python Runtime uses Python packaging metadata and installation/loading
  machinery;
- a Web Runtime uses a Module Federation Host and its manifest/loading
  machinery.

The common role name is **Distribution Consumer**. The qualified term matters:
`consumer` alone is ambiguous between a person, a Peer, and a software
component. `pip` is one possible tool used by a Python Distribution Consumer;
the Module Federation Host is the Web Distribution Consumer implementation.

The Peer supplies only the deployment-state integration needed by the Host SDK,
such as:

- current Peer identity and installed/enabled/configuration snapshots;
- compare-and-set style enabled/configuration persistence operations.

The Host SDK may know `InstalledExtension`, `PeerId`, `ExtensionConfig`, and
enabled intent. It does not know SQL, PostgREST, table names, UUID-array columns,
or transaction implementation. The state port translates those semantic
operations to the Peer's actual storage.

The Extension does not access Sources, Resolvers, routes, UI, or other Peer APIs
through the Host SDK or state port. It imports/calls the Peer implementation
directly. Under the current model that may include internal modules rather than
a restricted public API package.

Registry/native endpoint access, Distribution selection/acquisition/loading,
and lifecycle driving belong to the Host SDK. Concrete persistence stays behind
the state port. Core API calls and Extension-owned resource cleanup do not route
through the Host SDK. Developer Kits, build tools, conformance tools, and
publisher/CD clients remain a separate development-time product.

## Pre-Registry Peer Lifecycle Evidence

The two Peers did not originally implement the same lifecycle:

### `core-py`

- imports the Extension class and calls `on_start(app, extension)`;
- `on_start` validates/configures the Extension and immediately registers
  FastAPI routes, Sources, and Resolvers;
- disable/shutdown calls `on_close`, whose base behavior persists config;
- there is no explicit initialized-but-inactive state, separate deactivate
  phase, or module-unload phase.

This is effectively a one-session `start/close` model, although the original
implementation did not reliably withdraw every published contribution.

### `client-web`

- explicitly models `load -> initialize -> READY -> activate -> ACTIVE`;
- disable calls `deactivate` and returns to `READY`, deliberately retaining the
  initialized Module Federation module;
- re-enable from `READY` calls only `activate`;
- application shutdown performs `deactivate -> dispose/unload -> UNLOADED`.

This is a public two-phase model: disabled can still mean loaded and initialized.
The current Twitter Extension nevertheless registers a Resolver as a module-
import side effect, so the intended inactive boundary is not actually enforced.

The evidence does **not** justify lifecycle convergence. The earlier single
`start(context)` proposal over-corrected the thin Runtime problem: it introduced
an `ExtensionScope` abstraction that was not a product concept and erased
Core's explicit `on_close` resource-release hook. That candidate is withdrawn.

Lifecycle and registration belong to each Extension API Profile:

- Core Python may retain and refine its natural `on_start` / `on_close` model,
  with explicit Source, Resolver, and protocol-route registration APIs. An
  explicit close hook is valuable because the Extension owns resources whose
  release cannot always be inferred by the Host SDK.
- Client Web may retain a Web-specific load/initialize/activate/deactivate/
  dispose model if each boundary has observable semantics. Its import-time
  Resolver registration remains a defect because it bypasses those boundaries.
- Neither API has to expose the same hook names, number of phases, context
  object, or registration primitives.

There is no `ExtensionScope` concept. The Host SDK tracks the loaded Extension
instance and calls its profile-specific lifecycle. The Extension accesses Peer
implementation APIs directly and owns its resources. Whether those APIs later
gain symmetric cleanup handles is a Peer API evolution question, not part of a
universal Host SDK contract.

## Common Product Invariants, Not A Common Callable API

What remains language-neutral is smaller than an Extension lifecycle API:

- Extension Name and exact Extension Release version;
- pre-download Distribution Descriptor;
- compatible Peer/Host SDK implementation identity and version range;
- deployment `installed`, per-Peer `enabled`, and process-local `running`
  distinctions;
- observable operation guarantees such as failed enable not persisting enabled
  state and disable attempting to withdraw active contributions.

These are Registry/deployment contracts and behavioral conformance requirements.
They do not require Python and Web to implement one shared interface or state
machine.

Likewise, there need not be one language-neutral Runtime Adapter API. Each Host
SDK defines only the native deployment-state port it needs while respecting one
shared architectural constraint: the Host SDK must not know the concrete
database schema, and the state port must not absorb Registry resolution,
Distribution loading, Core API mediation, or Extension-developer
build/publication responsibilities.

## Product Contribution Points — Separate Concept

Do not call these installability capabilities. They are Extension-provided
product contribution points:

- Source
- Resolver
- Storage
- Sink
- constrained Protocol/API
- client UI/rendering contribution
- configuration schema and configuration lifecycle

Each Extension API Profile owns the lifecycle and contribution model that
makes sense for its host. A Core Python Source registration API and a Client Web
renderer registration API are not language bindings of one universal callable
Extension API.

## Current Peer-coupled API Reality

There is no standalone Core Python Extension API today:

- Core Extensions import `app.business.*`, `app.schemas.*`, `app.engine`, and
  `libs.*` directly;
- `inkcre-core` is application metadata with package/distribution mode disabled,
  so a third-party wheel cannot currently declare a resolvable dependency on a
  public Core API package;
- the existing `ExtensionBase`, `on_start/on_close`, Source/Resolver base
  classes, database schemas, managers, and FastAPI objects collectively form a
  de facto Peer-coupled contract;
- Client Web has a stronger package boundary through `@inkcre/core`, but it is
  still the whole Client Core package rather than a dedicated Extension API.

The previous Core Python candidate invented a stable public Core API and cleanup
handles. It is withdrawn. Preserving unrestricted Peer imports is a coherent
design choice, but it has a direct compatibility consequence: the pre-download
claim must be against a compatible Peer implementation/version, because there
is no narrower independently versioned API boundary to compare.

For Core Python, standard wheel metadata can still describe Python and third-
party dependencies, but it cannot prove compatibility with unversioned
`core-py` internals. Registry metadata or a future native metadata extension
must therefore expose the producer-tested compatible Core Peer version/range.
For Client Web, `@inkcre/core` and MF shared metadata already provide part of
that Peer-version compatibility signal.

## Accepted Compatibility Version Authority

There is no additional Extension API version. The version of the Peer/Host SDK
implementation against which a Distribution is built and tested **is** its
Extension API compatibility version:

```text
Core Python Distribution
  -> compatible core-py / embedded Core Host SDK version range

Client Web Distribution
  -> compatible @inkcre/core / embedded Web Host SDK version range
```

Each Peer repository owns and releases this version. The Registry does not mint,
translate, or synchronize a second API version; it preserves the producer's
declared compatible range and exposes it before download. The Host SDK compares
that range with its own authoritative implementation version.

This model is analogous to a package importing public or private symbols from
another package: the producer owns the claimed dependency range, and using
unstable internals increases the probability that the claim becomes wrong. It
does not require the dependency to have a separately carved plugin API.

## Accepted Compatibility Range Policy

Compatibility uses producer-declared SemVer ranges by default; exact versions
remain valid for fragile internal dependencies. While Peer/Host SDK versions are
pre-1.0, InKCre applies the explicit convention that PATCH releases preserve
Extension compatibility and MINOR releases may break it. Registry admission
validates range syntax, while the producer owns the truth of the claim and the
Host SDK evaluates it before download.

## Entry Discovery Is Still Required

Allowing arbitrary Peer imports eliminates a restricted API surface, but it does
not eliminate the Host SDK's need to locate the one Extension entry inside a
Distribution. That entry convention belongs to each API Profile's native
Distribution semantics:

- Core Python can use a standard Python package entry-point group whose value
  resolves to the existing Core Extension class; the class may continue to use
  the Peer-defined `on_start/on_close` and import any Core internals;
- Client Web can use its Module Federation manifest/remote and a documented
  exposed module whose default export follows the Client Web lifecycle.

The entry convention is not a new public Core API package. It is the minimum
loader handshake between the Distribution Consumer and Extension code. Using a
Python package entry point avoids hard-coding `extensions.<id>.Extension`, which
cannot safely represent namespaced Extension Names and couples package/module
layout to Registry identity.

## Accepted Minimum Meaning Of Extension API

This format-native loader handshake already constitutes an Extension API. An
Extension API does not require a separately published SDK or a broad restricted
Core surface. At minimum it is the versioned contract between one Host SDK and
one Distribution:

```text
native Distribution metadata and entry discovery
  + expected entry object/type
  + Peer-specific lifecycle calls
  + Host SDK implementation version compatibility
```

Everything the Extension imports after loading may remain ordinary Peer
implementation access. Python entry points and MF exposed modules are the two
MVP entry mechanisms; their lifecycle shapes remain intentionally different.

## Accepted Core Model Boundary

The earlier conclusion was directionally incomplete. A Core Extension already
inherits `ExtensionBase`; the natural Extension API is the behavior and semantic
model supplied by that base class. Configuration should not be passed as an
ad-hoc lifecycle context; validated configuration is available through inherited
`ExtensionBase` behavior. Extension-level persistent state is not added in this
MVP.

The Host SDK owns that Extension-facing model: its types, validation, mutations,
and lifecycle visibility. Before `on_start`, it privately binds the loaded
Extension class to the installed Extension identity and the Peer persistence
implementation. The Extension then uses inherited config behavior during its
lifetime and keeps explicit `on_start/on_close` hooks.

This does **not** make the current SQLModel database row part of the Extension
API. The current class called `ExtensionModel` is simultaneously a persistence
mapping and a lifecycle input. Those concerns must be separated:

```text
Extension
  inherits ExtensionBase
    -> Host SDK-owned Extension-facing model and config operations
    -> explicit on_start/on_close

Host SDK internal binding
  -> Peer persistence implementation
  -> concrete database record (private; never exposed to Extension)
```

It is reasonable for the Host SDK to own an API-level Extension model, but that
model must not be the SQLModel table object. Reusing `ExtensionModel` for both
would preserve the very coupling this review is removing. This does not prohibit
an Extension from voluntarily importing Core database internals; it only keeps
that producer-chosen dependency out of the mandatory lifecycle ABI.

## Current State Persistence Evidence

The current Core schema does **not** give an Extension record a `state` field:

- `extensions` contains only ID, version, enabled Peer IDs, nickname, config,
  and config schema;
- the later Registry `extension_installations` model also contains config and
  config schema but no state;
- `ExtensionBase` exposes config validation/update helpers but no state API.

Persistent synchronization state already exists one level lower. Every
`sources` record has deployment-shared JSON state, and `SourceBase` exposes
`get_state()/set_state()`. Current Mail, Telegram, GitHub, Twitter, and RSS
implementations use it for values such as `last_uid`, `last_update_id`, and
`latest_tweet_id`. Therefore the example “instance A reaches item 25 and B
continues from 25” is already supported when that cursor belongs to one Source
instance.

Adding deployment-shared **Extension-level** state would be a genuine new
product/API capability, not merely exposing a field that already exists. It is
excluded from this Registry MVP and requires a separate task if a use case is
found whose owner is the Extension as a whole rather than a Source or another
existing domain resource.

The accepted access policy for this MVP is:

- configuration is validated and exposed read-only to Extension code; its
  writer is the user/deployment management path through the Host SDK;
- no Extension-level persistent state API is introduced;
- existing Source-instance state remains available through `SourceBase`;
- process-local state remains ordinary implementation memory;
- installation version and enabled intent remain Host SDK-managed deployment
  state, not Extension-writable values.

The read-only configuration choice expresses authority and mutation policy. It
is not needed to make configuration distinguishable from state; those terms
already carry different meanings, and allowing a future explicit config write
would not inherently merge them.

## Next Design Surface

Review Batch 02 is closed as an accepted redesign. The next queue item is Batch
03: replace the generic canonical target-manifest model with format-native
Distribution hosting surfaces and revisit the embedded Python bundle.

## Status

Accepted redesign; implementation remediation remains pending. The Peer/Host
SDK implementation version is accepted as the Extension API compatibility
version; ranges are the default and exact versions remain
available. Format-native entry discovery plus the Peer-specific entry/lifecycle
shape is accepted as sufficient to constitute an Extension API. Core Python
uses inherited `ExtensionBase` behavior for configuration;
the Host SDK owns that Extension-facing model while the concrete SQLModel record
remains private persistence. The single lifecycle, `ExtensionScope`, Host SDK
mediation of Peer API calls, removal of `on_close`, and invented stable Core
Python API surface are withdrawn. Extension-level persistent state is excluded
from this MVP; existing Source state remains Core-owned.
