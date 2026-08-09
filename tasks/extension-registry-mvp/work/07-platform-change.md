# Product Question 07 — Peer Admission And Platform Change

## Previous Result

Question 06 assigned compatible-target selection to the extension runtime adapter, accepted stable selection among equal candidates, and locked the result to exact target identity and artifact digest.

## Question

What happens to incompatible Extensions when a user authorizes a new peer or a peer/runtime upgrade?

**Status**: Accepted with the bounded scope below.

## Verified Existing Capability

InKCre already persists per-peer enablement. The shared `extensions.enabled` UUID array lists the peers/clients for which an Extension is enabled; an empty array means disabled everywhere. Both `core-py` and `client-web` add or remove only the current/requested peer UUID.

Sources: [`core-py` Extension model](../../../../core-py/app/schemas/extension/main.py), [`core-py` enable/disable](../../../../core-py/app/business/extension/main.py), [`client-web` enable/disable](../../../../client-web/packages/core/src/extension/base.ts).

Therefore:

- a newly joined peer starts with existing Extensions disabled because its UUID is absent;
- a runtime upgrade that makes an enabled Extension incompatible can disable that Extension only for the affected peer;
- compatible peers remain enabled and keep their exact bindings.

There is no need for a global-disable fallback in the current model.

## Nextcloud Reference

Nextcloud treats the platform upgrade as authoritative over apps: its official upgrade guidance tells administrators to disable third-party apps before the server upgrade and re-enable them afterward. This is broader than InKCre needs, but supports the same priority direction—an app does not block an authorized platform upgrade.

Source: [Nextcloud upgrade prerequisites](https://docs.nextcloud.com/server/stable/admin_manual/maintenance/upgrade.html#prerequisites).

## Accepted Behavior

1. Peer admission and peer/runtime upgrades are explicit user-authorized platform operations.
2. Before confirmation, show the Extensions that will become unavailable on the affected peer and that they will be disabled there.
3. Once authorized, perform the platform operation and remove only that peer from each incompatible Extension's enabled set.
4. Preserve the shared installed Extension Version, other peers' enablement, and their exact target bindings.
5. A compatible Extension keeps its existing binding; the platform operation does not opportunistically switch targets.
6. Re-enabling a disabled Extension later requires a compatible target and a new exact binding for that peer.

Uncontrolled environment drift, such as an unexpected browser compatibility regression, is outside the MVP product scope. The Registry does not promise to predict or remediate it. Ordinary runtime load errors remain observable through the peer's existing failure behavior, but no new drift-management subsystem is designed here.

## Result

Planned platform evolution proceeds after impact disclosure and per-peer disablement of incompatible Extensions. It is not blocked by Extension coverage. The compatibility gates for Extension install, enable, and version upgrade continue in Question 08.
