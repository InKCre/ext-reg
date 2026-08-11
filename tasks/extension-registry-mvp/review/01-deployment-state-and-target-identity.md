# Review Batch 01 — Deployment State And Target Identity

## Questions

1. How does one shared installed Extension Version coexist with different target bytes per peer, and where is that binding persisted?
2. Are `python-core-v1` and `web-module-federation-v1` target keys, and who owns the apparent version suffix?
3. Should `extension_installations` and `extension_peer_bindings` be one table?

## Evidence

- `core-py` persists one `extension_installations` row keyed by `(namespace, name)` with one exact `version` and shared configuration.
- It persists zero or more `extension_peer_bindings` rows keyed by `(namespace, name, peer_id)`, each containing the installation version, producer target key, and canonical target digest.
- A deferred composite foreign key from binding `(namespace, name, version)` to installation enforces that every persisted binding names the shared installed version.
- Enable starts the selected exact target and writes the binding last; disable stops runtime effects and deletes that peer's binding last. Startup restores only bindings belonging to the current peer.
- Both reported names are producer-supplied `target_key` values in peer-owned `target-publish.json` files. Registry contract D023 treats a target key as an immutable release-local slot with no compatibility semantics.
- The actual Registry-owned format identifiers are separate values: `python-bundle-v1` and `module-federation-esm-v1`.

## Diagnosis

- The `peer binding` is exactly the persisted association from one deployment peer to one target key and canonical target digest under the shared Extension Version.
- Separate installation and binding relations are relationally coherent, but coherence does not prove that exact target selection belongs in deployment state. The current binding combines per-peer enablement with an exact distribution lock.
- Per-peer enablement already existed as the `enabled UUID[]` value on the shared `extensions` row. A separate binding table is necessary only if the product promises that the exact selected target remains pinned across peer restarts. That promise was introduced by the implementation rather than requested by the product.
- If every artifact beneath one Extension Version is semantically that same product version, an adapter can resolve any compatible immutable distribution on enable or cold start. Adding a new compatible distribution may affect a later resolution, as adding a wheel can affect a later installation of one PyPI release; it does not change the shared installed Extension Version.
- Exact content integrity remains necessary, but it can stay inside Registry storage and native distribution responses. It does not need to become deployment business state.
- The current target-key examples are misleading. Their `v1` suffix looks like a Registry-standard protocol version, but the key is publisher-owned identity metadata. No global authority owns that suffix. Format and API contract versions already have separate Registry-owned fields. This is an obscurity defect even though runtime behavior is deterministic.
- The previous proposal to hash “capabilities” reintroduced a rejected two-sided vocabulary. With format-native Registry APIs, no custom cross-format key is required: Python and Module Federation tooling can identify and resolve their native Distributions. Content digests remain Registry/storage/native-protocol integrity metadata rather than deployment state.
- A Registry can expose several format-native read APIs over one canonical release model. A Python adapter can consume a PyPI-compatible index/distribution surface while a Web adapter consumes an immutable Module Federation remote surface. This is simpler for peers than requiring every runtime to understand the Registry's generic file-manifest protocol.

## Proposed Disposition

- Eliminate Extension Coordinate as a separate product concept. `inkcre/twitter` is the canonical Extension Name; its first segment still scopes publisher ownership.
- Keep one deployment-wide Extension record containing canonical Extension Name, exact version, shared configuration, and the existing per-peer enabled set.
- Prefer migrating the existing `extensions` table over maintaining parallel legacy and Registry installation tables, subject to the explicit migration audit in Batch 04.
- Remove `extension_peer_bindings` unless review uncovers a real product requirement for exact per-peer distribution pinning across restarts.
- Let each Runtime Adapter resolve a compatible immutable distribution for the shared version when enabling or cold-starting. Native runtime/package state may cache materialized bytes, but the shared database does not own the selected distribution.
- Retire arbitrary `target_key`. Prefer format-native Distribution identity and resolution; use an opaque Registry-internal row identity only if storage needs one.
- Retain content hashes internally for immutable storage and transport integrity; do not expose file-by-file hashes as deployment state.
- Design format-native Registry surfaces—initially PyPI-compatible Python distribution and Module Federation remote delivery—over one common Extension release/control-plane model. Batch 03 owns the exact API and storage design.

The preferred deployment relation is therefore conceptually:

```text
extensions
  name          canonical Extension Name, primary key (for example inkcre/twitter)
  version       exact installed Extension Release version
  enabled       Peer UUID[]
  nickname      optional product nickname
  config        shared Extension configuration
  config_schema shared configuration schema
```

The Registry may internally store the ownership scope and local slug in
separate columns, but Deployment state and public product vocabulary treat the
combined value as one Extension Name.

## Accepted Re-resolution Rule

Removing persisted target binding means an enabled peer may resolve another compatible distribution of the same Extension Version after a cold start or explicit re-enable. The recommended product rule is to allow this: all distributions under one version must implement the same Extension product version, and replacing bytes with changed product behavior requires a new Extension Version. Exact local package/cache state is a runtime concern, not shared deployment state.

There is no universal Distribution ID to persist. Python packaging and Module
Federation identify and resolve their Distributions through their native API
surfaces. Registry-internal row IDs and content digests remain implementation
and integrity details.

## Status

Accepted redesign. Implementation remains unchanged and requires a later impact handshake.
