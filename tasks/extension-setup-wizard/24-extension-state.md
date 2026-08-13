# Extension State Proposal

## Why Setup Changes the Earlier MVP Boundary

The Registry MVP previously deferred general Extension state because no
accepted vertical slice required it. Twitter setup now supplies that need:
OAuth authorization produces account credentials and a resumable callback
transaction that must survive Core restart, Web closure and Peer handoff. These
facts are neither user-declared config nor Source-instance state.

Core already has a Source precedent: `sources.state` is deployment-durable and
Source-owned. It confirms the product distinction, but its current whole-object
`get_state`/`set_state` implementation is not a concurrency contract to copy.
Sir has already established that shared-state concurrency belongs to Core's
state authority rather than Extension code or an Extension Host SDK.

## Accepted Canonical Model

Add one non-null JSON object to the existing canonical Extension installation
record:

```text
extensions
  name
  version
  enabled[]
  nickname
  config
  config_schema
  state        JSON object, default {}
```

Do not add an `extension_states` table. One installed Extension already has one
deployment-wide identity and one state authority; a second one-to-one relation
would add joins and lifecycle without adding a distinct owner.

The semantic split is:

| Authority | Written by | Twitter examples |
| --- | --- | --- |
| Extension config | User/operator through validated Extension commands | OAuth App Client ID and Client Secret |
| Extension state | Extension through its Core Host SDK | account tokens and identity; OAuth transactions |
| Source config/state | Source domain | bookmark Source schedule/config and collection cursor |
| Runtime memory | one running Peer process | HTTP clients, locks, loaded module objects |

Secrets may appear in config or state under the already accepted trust boundary;
secrecy does not define the domain category.

## Core State Authority and Host SDK Boundary

The Core state authority owns persistence, serialization and cross-Peer
concurrency, ultimately backed by database transactions and constraints. The
Extension Host SDK is only the typed interface through which Extension code asks
that authority to read or mutate state; it does not itself guarantee concurrency
or become the state owner.

A concrete Extension declares both validated types conceptually:

```python
class TwitterExtension(
  ExtensionBase[TwitterConfig, TwitterState],
  config_cls=TwitterConfig,
  state_cls=TwitterState,
):
  ...
```

The Extension receives typed config/state through `ExtensionBase` operations;
the SQL model and database session are not passed to Extension code. The Host
SDK delegates state mutation to one Core-owned semantic operation. HLD selects
the smallest authoritative implementation: a database transaction with exact-row
`SELECT ... FOR UPDATE`, described in
[Canonical Extension State](32-hld-extension-state.md). Extension code and the
Host SDK do not implement cross-Peer locking themselves.

State is not a generic form surface, so the MVP does not persist a
`state_schema` merely for UI generation. The concrete Extension state type is
the validation and migration authority. The Twitter Web Distribution consumes
the Twitter setup projection and commands rather than treating raw state JSON
as its UI contract.

## Twitter State Shape

The product shape is intentionally narrower than an exact schema:

```text
TwitterState
  account?
    access_token
    refresh_token?
    expires_at
    scopes[]
    user_id
    handle
  oauth_transactions
    <opaque reference>
      provider_state_binding
      pkce_verifier
      status: pending | succeeded | failed | expired
      created_at
      expires_at
      error_category?
```

Transactions are TTL-bounded and cleaned after a bounded observation window;
their opaque reference is not a credential and their polling projection never
returns provider state, PKCE or tokens. A successful callback commits account
state and terminal transaction status atomically so polling cannot observe
success without restorable credentials.

## Lifecycle Invariants

- State survives Peer disable/re-enable, Core restart and Web closure.
- It is not scoped to the Core endpoint that handled a command.
- Wizard step position and `setup_complete` are never stored in it.
- Extension readiness remains a projection over config, state, Sources and
  runtime availability.
- Uninstall removes the Extension row and therefore its config/state, without
  inspecting or deleting Sources. Unreachable Source types are handled by the
  Source domain's existing lifecycle logic.
- Upgrade, rollback, reconfiguration and the first-release compatible state
  contract are closed in the lifecycle proposal and HLD; a general migration
  engine remains intentionally outside the task.
