# Extension State and Setup Lifecycle Proposal

## Accepted Product Model

### Reopen and manage

Once setup is ready, the same card action reopens the Extension-owned wizard as
a setup summary and management flow. It still derives truth from config, state,
Sources and runtime availability; it does not become a separate settings store.

### OAuth App reconfiguration and reconnect

- Changing Client ID/Secret while an account is connected must preview the
  impact and require explicit confirmation.
- Committing different App credentials atomically updates config and invalidates
  the account authorization and outstanding OAuth transactions that were bound
  to the old App. Sources are preserved and readiness becomes incomplete until
  reconnection succeeds.
- Reconnecting with unchanged App credentials does not replace a working account
  when authorization begins. A successful callback atomically replaces account
  state; failure or expiration leaves the previous working account intact.

### Disconnect

Disconnect is an explicit command. It clears account credentials and outstanding
OAuth transactions but preserves OAuth App config and Twitter Sources. The
Extension remains installed and enabled, while readiness returns to
`disconnected`; Core must not accept new Twitter collection work until a usable
account is restored.

### Peer disable and re-enable

Disabling a Web Peer removes the local setup entry because its Web Distribution
is no longer loaded. Disabling a Core Peer removes that command/runtime endpoint.
Neither operation deletes deployment-wide config, state or Sources. Re-enabling
a Core Peer restores from shared state and revalidates it; operational failure is
reported as readiness, not by erasing durable facts.

### Upgrade and rollback

The first MVP does not add a general Extension-state migration engine or a
Registry state-compatibility declaration. Core therefore has no objective,
side-effect-free way to prove that a different Distribution version can consume
non-empty state. Version change is allowed only when the canonical state is the
empty object; otherwise upgrade or rollback fails before changing the installed
version or state. Same-version install remains idempotent. The initial
`0.1.1 -> 0.2.0` Twitter cut is allowed because the newly added state column is
empty. A later task must define an explicit migration contract before preserving
non-empty state across versions; Core must not infer compatibility from Python
types by installing untrusted future bytes into the active interpreter.

### Uninstall

Uninstall still requires every Peer to be disabled. It removes the canonical
Extension row and therefore its config and state. It does not inspect, block on,
or delete Source records. Source is a separate authority and already owns the
behavior for records whose type is no longer reachable. Reinstalling a
compatible Distribution may make that type reachable again without reconstructing
Source records from Extension state.

### OAuth transaction cleanup

Pending and terminal OAuth transactions have bounded expiry and observation
windows. Cleanup removes only expired transaction entries. It does not remove a
working account, change wizard progress, or affect Sources.
