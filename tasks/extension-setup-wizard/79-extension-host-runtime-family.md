# Extension Host Runtime Family and Repository Topology

> **Superseded implementation boundary:** D043 moved `ExtensionManager` and
> `ExtensionBase` into each per-Peer Runtime, restored the Core/Client rich
> Active Record model and rejected generic Repository/Port layers. This file
> remains historical topology evidence; use the active Handshake and plan.

## Correction

The local-first Python activation defect exposed a larger repository-boundary
error. It is misleading to describe the Python Host Runtime as a new isolated
repair package while leaving the Web and Core implementations embedded in their
Peer repositories.

`ext-reg` owns three first-class product unit families:

```text
Extension Registry
  - Release catalog and native Distribution hosting/admission

Extension Developer Toolkit
  - build, inspect, publish and preview developer workflows

Extension Host Runtime family
  - one implementation per technology stack / Peer type
  - consumes the Registry's native Distribution API
  - prepares and loads native Extension modules inside that Host
```

The current Core Python and Client Web runtime implementations are functional
evidence, but their ownership is wrong: each Peer repository has accumulated
its own Registry consumer and native Distribution loader; Client also embeds
the Web module lifecycle. They must become consumers of Runtime packages
managed and released from `ext-reg`. Core-specific `ExtensionBase` lifecycle
and publication remain Core's Host adapter rather than moving across the
dependency boundary.

## Runtime Family, Not One Universal Runtime

The repository must not force Python and Web into one lifecycle, contribution
or registration model. Runtime commonality is limited to product semantics and
language-neutral Registry contracts:

- deployment `installed` Release selection;
- Peer-local/session-local Distribution `present` state;
- runtime `running` state;
- exact native Distribution association;
- local-first consumption where the technology provides durable local
  presence;
- explicit native-consumer errors; Web additionally owns its structural module
  lifecycle errors.

Each Runtime owns the happy path of its native consumer:

- the Core Python Runtime uses wheel metadata, the current interpreter,
  standard entry points and pip;
- the Client Web Runtime uses native Module Federation manifest/Host behavior
  and the browser/module runtime;
- later Peer types receive separate Runtime packages rather than conditionals
  inside either existing package.

The Host SDK/Extension API identity remains Peer-type-specific (`core-py`,
`client-web`, and future peers). Repository co-location does not create a single
cross-platform Extension API.

## Dependency Topology

```text
core-py
  -> Core Python Extension Host Runtime
       -> Registry native Python contract
       -> wheel/pip/entry-point consumer

client-web
  -> Client Web Extension Host Runtime
       -> Registry native Module Federation contract
       -> Module Federation Host consumer

Extension Developer Toolkit
  -> shared language-neutral/native metadata rules

Extension Registry service
  -> shared language-neutral/native metadata rules

Host Runtime packages
  -> shared language-neutral/native metadata rules
```

No dependency points from a Runtime into a Peer's database, routing or product
business modules. Peers compose Runtime results with Host-specific persistence
and contribution behavior; Runtime does not call those Peer adapters.
Extensions may still use the Host SDK and directly import the Peer
implementation surfaces admitted by that Host API; Runtime extraction does not
invent an isolation layer.

## Repository Shape

Exact directory and distribution names are an implementation-plan decision,
not a product question. The names should remain explicit and unsurprising. A
representative structure is:

```text
runtimes/
  core-py/       # Python distribution
  client-web/    # npm distribution
toolkit/         # independent Developer Toolkit distribution
src/...          # Registry service distribution
contracts/       # language-neutral generated/public contracts
```

The packages release independently. The Registry service must not become a
runtime dependency bundle, and the Toolkit must not become a production Host
Runtime.

## Installed and Present Semantics

An `extensions` row means the Extension Release is installed in the deployment.
It is valid to insert that row before any or every Peer has acquired native
bytes. Installation is therefore deployment-level and may be lazy at each Peer.

`present` is consumer-local observation and is never persisted in the shared
database:

- Python derives it from the exact installed Distribution and its installed
  metadata in the current environment;
- Web derives it from the current Module Federation/runtime session and may
  lose it with page/runtime teardown;
- a rebuilt Peer derives it again rather than trusting a stale shared flag.

No `present` column, peer binding, target digest or local cache record is added
to `extensions`. `enabled[]` remains deployment intent for each Peer; `running`
and `present` remain runtime observations.

## Migration Strategy

### A — Runtime-family inventory

- inventory the exact Registry client, native consumer, lifecycle and error
  surfaces currently embedded in Core and Client;
- separate reusable Runtime behavior from Peer-owned database, routing,
  delegation, config/state and UI behavior;
- identify current duplicate or conflicting semantics before moving code.

### B — Shared contract placement

- keep Release/native association schemas language-neutral;
- put wheel installed-metadata generation/admission in shared pure rules used by
  Toolkit, Registry service and Python Runtime;
- avoid a source-code dependency between Python and TypeScript Runtime packages.

### C — Python Runtime extraction and correction

- release the Core Python Runtime from `ext-reg`;
- implement installed-metadata discovery, local-first preparation, Registry
  fallback, pip acquisition, and entry-point module load/unload there;
- migrate Core to the locked Runtime release and delete its embedded duplicate.

This batch resolves the observed disable/re-enable failure.

### D — Web Runtime extraction

- move the existing Registry Release/Module Federation consumer and Web
  lifecycle orchestration into the Client Web Runtime package;
- preserve Client-owned database state port, Peer selection, popup shell and
  application UI;
- migrate Client to the locked Runtime release and delete its embedded
  duplicate.

This is an ownership correction, not a reason to impose Python's local-presence
or lifecycle model on the browser.

### E — Cross-repository adoption

- publish each Runtime through its native package manager;
- lock it in its Peer repository;
- require Peer feature PRs to consume the released package rather than copying
  a temporary implementation back into the Peer;
- resume setup-wizard preview acceptance only after Core PR #65 uses the Python
  Runtime local-first path.

## Acceptance Criteria

1. `ext-reg` explicitly manages Registry service, Developer Toolkit and the
   per-tech-stack/per-Peer-type Host Runtime family as separate release units.
2. Core and Client consume their corresponding Runtime packages and no longer
   own duplicate Registry/native-consumer/module-loader implementations; Web
   additionally consumes its four structural module lifecycle hooks while
   retaining Vue/setup projection in Client.
3. Python and Web share product terms and Registry contracts without sharing a
   forced lifecycle or contribution API.
4. An `extensions` row remains deployment-installed truth and permits lazy
   native acquisition by individual Peers.
5. `present` remains a derived local/session observation and is never written
   to the shared database.
6. The Python Runtime resolves exact local presence before Registry I/O; the Web
   Runtime continues to follow native Module Federation Host semantics.
7. Runtime packages know no Core/Client database schema, Peer transport or
   product UI.

## Readiness Verdict

**Architecture direction is accepted and ready for an implementation plan.**

Wheel-installed metadata is required and no longer awaits product approval.
Package and directory names are delegated implementation choices. The remaining
work is evidence-based inventory and an exact extraction/release/adoption plan,
not another product-design round.
