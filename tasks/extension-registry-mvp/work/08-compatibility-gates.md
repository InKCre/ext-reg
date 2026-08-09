# Product Question 08 — Which Operations Require Target Coverage?

## Previous Result

Question 07 confirmed that InKCre already supports per-peer enablement. A user-authorized peer/runtime change proceeds after disclosing impact and disables incompatible Extensions only on the affected peer; it does not change the shared installed Extension Version or other peers.

## Question

Should target compatibility be required for every registered peer, or only for peers on which an Extension is being enabled or kept enabled across a version upgrade?

**Status**: Accepted with the MVP simplification below.

## Conflict To Resolve

The earlier coverage rule said Extension install/upgrade should prove compatibility for every participating peer. Per-peer disablement makes an all-registered-peers interpretation unnecessarily strict: an installed but disabled Extension does not load or execute on that peer, and a newly joined peer intentionally begins with existing Extensions disabled.

## Recommendation

Make compatibility gates follow enablement:

### Install

- Installing a published Extension Version creates the deployment-owned installed record.
- It is disabled for every peer by default, so installation does not require target coverage for disabled peers.

### Enable Or Re-enable

- The peer's extension runtime adapter must resolve, select, and bind a compatible target.
- If none exists, enablement fails without changing that peer's enabled state.

### Upgrade Or Roll Back The Extension Version

- Preflight every peer on which the Extension is currently enabled.
- If each enabled peer has a compatible target, atomically change the shared Extension Version and exact bindings.
- If some enabled peers lack coverage, block the version change. MVP does not provide an automatic disable-and-upgrade combined operation; the operator may disable affected peers separately and retry.
- Disabled peers do not block the Extension version change.

### Peer/Runtime Change

- Question 07 applies: disclose impact and disable incompatible Extensions only on the affected peer, because the platform operation has higher priority.

This preserves the single shared Extension Version while giving per-peer enable/disable real meaning. It also replaces the vague term `participating peer` with the operation's enabled-peer scope.

## Result

Compatibility gates follow per-peer enablement. Installation starts disabled everywhere; enablement requires one compatible target and exact binding; disabled peers do not gate future version changes. Extension-to-extension dependencies are explicitly outside MVP.
