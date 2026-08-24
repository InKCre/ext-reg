# Python Host Runtime — Local Distribution Presence

## Review Trigger

During PR #65 acceptance, `inkcre/twitter` was disabled on the Core preview and
then enabled again. Client Web reported:

```text
Extension management Peer returned HTTP 502 for inkcre/twitter.
```

The Core Host currently enters Registry resolution before inspecting the
current interpreter. Its effective path is:

```text
enable
  -> resolve exact Registry Release
  -> obtain Python association
  -> ask pip consumer to acquire
  -> discover that the exact Distribution is already installed
  -> activate
```

The ordering makes Registry availability a prerequisite for activation even
when the exact wheel is already present. The `502` is therefore not sufficient
evidence of a Preview Registry defect; it is first an Extension Host Runtime
boundary defect.

## Correct Product States

Three states must remain distinct:

- **installed**: deployment authority selected one exact Extension Release in
  the shared database;
- **present**: one Python Host has the exact native Distribution in its current
  interpreter environment;
- **running**: that Host activated the Distribution and published its runtime
  contributions.

The presence of an `extensions` row is the deployment-level installed truth. It
does not prove `present` on every Core Peer because installation is deliberately
lazy at the native-consumer boundary: a newly created or rebuilt Peer may have
to acquire the wheel when first enabled. Conversely, disabling an Extension
does not uninstall its wheel, so a later enable on the same environment must
not require the Registry. `present` is derived locally and is never written to
the shared database.

The resulting state transition is:

```text
deployment Release selection
  -> Host Runtime inspects local Distribution presence
       -> exact local Distribution present: activate locally
       -> absent: resolve native association from Registry, acquire, then activate
  -> running

disable
  -> stop/unpublish
  -> exact local Distribution remains present

re-enable
  -> inspect local presence
  -> activate locally without Registry I/O
```

An ephemeral Peer whose environment was rebuilt legitimately loses `present`;
its next cold restore may depend on the Registry again. That does not justify a
Registry call when exact local bytes and their installation identity remain.

## Unit Ownership

This behavior belongs to the Core Python member of the independently versioned,
platform-specific **Extension Host Runtime family** managed by `ext-reg`. It is
not an isolated repair package: Client Web likewise consumes a Web Runtime from
the same family, while retaining its different native consumer and lifecycle
model. Runtime behavior does not belong to:

- the Registry service, which hosts Releases and native Distributions;
- the Extension Developer Toolkit, which builds, inspects, publishes and
  projects developer outputs;
- Core's database or Peer delegation layer.

The dependency direction is:

```text
core-py
  -> Python Extension Host Runtime
       -> native Registry Release reader
       -> installed-Distribution discovery
       -> pip acquisition
       -> entry-point module load/unload

Extension Registry service
  -> serves Release/Python native read surfaces

Extension Developer Toolkit
  -> produces and validates installable Extension Distribution metadata
```

Repository co-location does not make one Runtime generic across platforms. The
Python Runtime remains tied to the `core-py` Host SDK and its Extension API; the
Web Runtime remains tied to `client-web` and native Module Federation Host
behavior. See
[Extension Host Runtime Family and Repository Topology](79-extension-host-runtime-family.md).

## Runtime Boundary

The Python Host Runtime owns:

- native Release and Python-association value models;
- exact local Distribution discovery;
- local installation-identity validation;
- Registry/Simple/pip acquisition when, and only when, local presence is
  absent;
- loading the standard `inkcre.core.extensions` entry point;
- native module handle ownership and unload/origin mechanics.

It does not know:

- `extensions` or any other database table;
- deployment install rows or `enabled[]` persistence;
- Peer selection, capability delegation or lease state;
- Core HTTP routes, PostgREST or management response codes;
- Twitter setup, Source, Cron or Job product behavior.

Core supplies a selected `{name, version}` and lazy Registry origin for the
acquisition fallback. Core retains `ExtensionBase` subclass admission,
`on_start/on_close`, publication/claim compensation, config/state, installed and
enabled persistence, and management-protocol error mapping. This prevents a
Runtime-to-Core dependency or a second lifecycle coordinator.

## Installed Distribution Identity

Long-term local activation must not depend on a remembered Registry response or
infer identity from a project-name convention alone. The installable wheel must
carry Host-readable Extension metadata derived from the producer's
`[tool.inkcre-extension]` declaration and validated by the Developer Toolkit.

The installed metadata must be sufficient to establish, without network I/O:

- canonical Extension Name;
- exact Extension Release version;
- Python project identity and installed project version;
- Host SDK identity and compatible Host SDK range;
- standard entry-point group, name and object.

The implementation shape is a versioned, declarative metadata record shipped
inside the wheel's installed `.dist-info` data. It is build-time input and
installed Distribution metadata, not a peer binding, database row, digest, or
runtime cache. The Toolkit owns generation/admission rules; the Python Host
Runtime owns reading and validating the installed record. Registry admission
must consume the same pure metadata model so the remote association and wheel
cannot describe different Extension identities.

This avoids both weak local guessing and a new Core-owned persistence schema.
It also lets a Core upgrade re-evaluate the locally installed Host SDK range
without consulting the Registry.

## Runtime API Direction

The public Runtime surface should express the state transition rather than pip
commands or Registry HTTP calls. The exact Python names remain implementation
work, but the semantic shape is frozen:

```python
selection = ExtensionSelection(name="inkcre/twitter", version="0.2.1")

prepared = runtime.prepare_installed(
    selection,
    registry_origin=lambda: resolve_registry_origin(),
)
# prepare_installed performs exact local discovery first; Registry acquisition
# is only a local-miss fallback.

loaded = runtime.load(prepared)
# Core validates ExtensionBase and owns on_start/on_close/publication.
runtime.unload(loaded)
```

`prepare_installed` must return an exact local prepared Distribution or fail. It
must not resolve Registry configuration, refresh, re-resolve, revalidate yanking
state, or otherwise contact the Registry after exact local identity succeeds. A
caller uses the separate `resolve_install` path for a new Release;
load/activation is not that path.

## Migration Batches

### A — Python member of the Runtime family

- create the independently versioned Core Python Host Runtime package alongside
  the Client Web Runtime package family in `ext-reg`;
- move native descriptor models, Registry reader, installed-distribution
  discovery, pip acquisition and entry-point module loading behind its public
  API;
- keep the Developer Toolkit and Registry service as separate distributions;
- avoid introducing database or Peer abstractions into the Runtime.

### B — Wheel metadata contract

- define the versioned installed Extension metadata record;
- have Toolkit build/inspection derive and validate it from
  `[tool.inkcre-extension]` plus standard wheel metadata/entry points;
- update first-party Python Extension wheels to carry the record;
- have Registry Python admission use the shared pure model.

### C — Core adoption

- add the released Python Host Runtime as a locked Core runtime dependency;
- replace Core-owned Release/pip/discovery/module-loading implementation with
  the Runtime API while Core retains ExtensionBase lifecycle/publication;
- retain Core's database store, Peer delegation, publication adapters and HTTP
  error mapping;
- remove duplicate Core-native consumer code after adoption rather than keeping
  a compatibility path.

### D — Feature preview acceptance

- rebuild the PR #65 first-party wheel facade with the new metadata;
- update PR #65 to the released Runtime and rerun its preview;
- disable `inkcre/twitter`, make the Registry origin unavailable or invalid for
  that operation, and re-enable successfully from local presence;
- separately prove that a fresh environment with no local wheel still uses the
  configured Registry acquisition path;
- reconnect Client PR #71 and stop acceptance when the Twitter setup popup is
  available.

Commit, push, release, cross-repository mutation and deployment remain separate
authorization boundaries.

## Acceptance Criteria

1. A Python Host Runtime package, separate from Registry service and Developer
   Toolkit, owns local discovery, acquisition fallback and native module
   load/unload.
2. Core does not resolve a Registry Release when the exact compatible installed
   Distribution is locally present.
3. Local discovery uses installed declarative Extension metadata and standard
   wheel/entry-point metadata, not naming convention, digest, Core database
   fields or a remembered in-process Registry response.
4. Exact local absence invokes the native Registry/Simple/pip path once through
   the Runtime; a fresh/rebuilt Peer can still restore enabled intent.
5. Disable leaves local presence intact; re-enable on the same environment is
   Registry-independent.
6. Version change and first acquisition remain Registry-authorized operations;
   activation does not silently choose another version.
7. Core retains deployment/Peer/database authority plus `ExtensionBase`
   lifecycle/publication, and the Runtime imports no Core modules.
8. Core removes its duplicate consumer implementation after adopting the locked
   Runtime release.

## Readiness Verdict

**Product and ownership direction accepted and ready for implementation
planning.**

The wheel-installed metadata record is required. Its exact file/schema and the
Runtime package/API names are delegated implementation choices to be frozen in
the evidence-based plan; they do not require another product confirmation.
