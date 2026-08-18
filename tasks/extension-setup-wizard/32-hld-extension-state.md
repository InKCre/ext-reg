# HLD 2 — Canonical Extension State

## Persistence and Authority

Add one column to the canonical deployment relation:

```sql
ALTER TABLE inkcre.extensions
  ADD COLUMN state jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE inkcre.extensions
  ADD CONSTRAINT ck_extensions_state_object
  CHECK (jsonb_typeof(state) = 'object');
```

The table continues to represent one installed Extension Release for the whole
deployment. `state` is deleted with that row on uninstall. Sources remain
independent and are neither inspected nor deleted.

Core and PostgreSQL remain the state authority:

- the authenticated PostgREST role may read `state` inside the accepted Peer
  trust boundary, but cannot update it directly;
- a migration trigger rejects a non-empty `state` on direct insert, just as the
  existing trigger rejects a non-empty `enabled` value;
- only the Core service role mutates state through Core-owned operations;
- every mutation locks the exact Extension row with `SELECT ... FOR UPDATE`,
  validates the current and next values, and commits once;
- provider or other network I/O never runs while the row lock is held.

The current Core type named `ExtensionState` is actually an installed-row
projection. Rename it to `InstalledExtension`, and rename
`ExtensionStateStore`/`SQLExtensionStateStore` to
`ExtensionStore`/`SQLExtensionStore`. The projection keeps installation fields
and does not expose raw Extension state through the generic Core management
API. This removes the future ambiguity of `state.state` without changing the
canonical table.

## Core Host SDK Shape

Existing Extensions receive an empty validated state by default. A stateful
Extension binds a second model type:

```python
class ExtensionBase[ConfigT, StateT](
  config_cls=...,
  state_cls=EmptyState,
):
  @classmethod
  def get_config(cls) -> ConfigT: ...

  @classmethod
  def update_config(cls, next_config: ConfigT) -> ConfigT: ...

  @classmethod
  def get_state(cls) -> StateT: ...

  @classmethod
  def mutate_state(
    cls,
    transform: Callable[[StateT], StateT],
  ) -> StateT: ...

  @classmethod
  def mutate_config_and_state(
    cls,
    transform: Callable[[ConfigT, StateT], tuple[ConfigT, StateT]],
  ) -> tuple[ConfigT, StateT]: ...
```

`ExtensionBase` validates both sides of each transform with the Extension's
declared models. It passes a pure dictionary transform to a narrow
`ExtensionRuntimeRecord`; the Core store executes that transform inside its
transaction. SQLModel rows, sessions and locks never cross into Extension code.
After a combined mutation commits, `ExtensionBase.config` is replaced with the
committed validated config.

`ExtensionBase.config` remains the startup/last-local-commit snapshot needed by
existing Extensions; it is not a cross-Peer freshness guarantee.
`get_config()` reads and validates the current canonical row. Setup, OAuth,
token refresh and provider-client construction must call `get_config()` rather
than relying on the snapshot. This lets Core Peer B observe a credential change
committed through Core Peer A without making the Host SDK or process memory the
authority.

Configuration persistence is command-time, not teardown-time.
`ExtensionBase.update_config()` validates, persists through the runtime record,
then replaces the local snapshot; the Host management route uses the same
semantic operation for a running Extension. `mutate_config_and_state()` behaves
likewise for its atomic pair. Base `on_close()` performs no unconditional config
write. Otherwise a disabling Core Peer could overwrite a newer config committed
by another Peer with its stale startup snapshot.

The runtime record therefore adds these Core-owned callbacks:

```text
read_config() -> JSON object
read_state() -> JSON object
mutate_state(transform(JSON object) -> JSON object) -> committed JSON object
mutate_config_and_state(
  transform(config JSON, state JSON) -> (config JSON, state JSON)
) -> committed (config JSON, state JSON)
```

This is an Extension API surface because it is inherited from the Core Host
SDK. It is not a generic state service and does not promise that arbitrary
Extension code may retain a mutable state object between calls.

## Transaction Semantics

`SQLExtensionStore` owns fresh reads and transactional mutations in addition to
the existing install, config and enablement operations:

```text
read_config(name)
read_state(name)
mutate_state(name, transform)
mutate_config_and_state(name, transform)
```

For a mutation, Core:

1. begins a transaction;
2. selects `inkcre.extensions[name] FOR UPDATE`;
3. fails if the Extension is absent;
4. gives copies of the current JSON values to the pure transform;
5. validates that the result is a JSON object and writes it once;
6. commits and returns the committed value.

The Python process-local runtime lock may still serialize lifecycle calls in one
Core process, but it is not the cross-Peer authority. PostgreSQL row locking is.
Extensions do not perform their own distributed locking.

## Database Contract Cut

This is an additive database migration, not another clean reset:

- append one Alembic revision after the current head;
- bump `CORE_VERSION` and the root project version from `0.1.0` to `0.1.1`;
- bump `CONTRACT_REVISION` from `peer-database-runtime-v2` to
  `peer-database-runtime-v3`;
- update metadata, deployment profile, runtime contract, schema artifact,
  PostgREST checks and migration integrity;
- regenerate `client-web` database types from the exact Core branch image;
- keep `extension_installations` and `extension_peer_bindings` absent.

The store's version-change transaction and the relation's update trigger both
require `OLD.state = '{}'` before `version` may change. The store check happens
under the same locked installed row and before writing the new version; the
trigger prevents a direct PostgREST update from bypassing it. There is no attempt
to import the incoming Distribution as a migration probe. Non-empty state makes
a different-version install fail closed; same version remains idempotent.

All existing first-party Python Extension Host ranges
`>=0.1.0 <0.2.0` continue to accept Core `0.1.1`. Twitter `0.2.0` will require
`>=0.1.1 <0.2.0`, making the new state/callback API a pre-download
compatibility gate without reintroducing capability labels.

## Focused Verification

Core tests must prove:

- migration default, JSON-object constraint, insert trigger and direct-update
  denial for the authenticated role;
- state survives restart/Peer handoff and is removed with uninstall;
- a different-version install succeeds with empty state and is rejected without
  mutation when state is non-empty;
- two Core sessions serialize state mutation through the database row lock;
- a failed validation or transform rolls back both config and state;
- a second Core process reads a config/state commit made by the first before a
  freshness-sensitive provider operation, without restart or process messaging;
- disabling a Peer with an old startup snapshot cannot overwrite a newer config,
  while explicit Extension/Host config updates persist immediately;
- existing Extensions receive `EmptyState` without source changes;
- Extension code sees typed config/state methods but no database row/session;
- the generated contract is revision v3 and the rejected installation/binding
  relations remain absent.
