# Product Design

## Status

**Complete for MVP.** This document owns the task-local product contract admitted into High-level technical design. Implementation details, API shapes, storage schemas, and framework choices remain outside this file.

## Product Promise

InKCre Extension Registry is a public, hosted, multi-publisher package service for Extensions. It provides authenticated publication and anonymous discovery/download while keeping source in publisher-owned repositories.

First-party Extensions remain in peer repositories and publish through peer-owned CD under the reserved `inkcre` namespace. They use the same Registry protocol as any other publisher.

## Product Identity

- Extension coordinate: lowercase `namespace/name`.
- Each segment is 1–64 ASCII characters matching `[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?`.
- `inkcre` is operator-reserved.
- Extension Version uses the accepted strict SemVer profile.
- A version contains one or more independently published Technical Targets.
- A target has a producer-chosen immutable key subordinate to the version. The key identifies an artifact slot but does not determine compatibility.
- Exact executable identity is the target artifact digest, not the Extension Version or target label.

## Actors And Authority

- **Anonymous consumer**: reads public metadata and downloads published artifacts.
- **Namespace owner / publisher**: publishes within a manually provisioned namespace using scoped credentials.
- **Extension runtime adapter**: evaluates target compatibility, selects a target, and binds its exact digest for one peer.
- **Deployment operator**: owns installed version, configuration, per-peer enablement, and uninstall.
- **Registry operator**: provisions namespaces, reserves `inkcre`, and may block abusive content.

The Registry validates and indexes compatibility declarations and returns candidates. The runtime adapter owns platform evaluation, preference, selection, and binding. Registry publication state never owns deployment `installed`, peer `enabled`, or runtime `running` state.

## Registry Release State

### Preparing

- The first accepted target creates a non-public Extension Version.
- The same target key and digest may be retried idempotently.
- Reusing a target key with a different digest is a conflict.
- Distinct target keys may be appended independently by authorized CD pipelines.

### Published

- An authorized publisher explicitly publishes a preparing version once it has at least one target.
- Public metadata and artifact download become anonymously readable.
- Existing target key/digest pairs and release semantics are immutable.
- New distinct targets may still be appended and become public without redefining a globally required target set.

### Yanked Or Operator-blocked

- A publisher may yank a version so new resolution, install, and enable operations exclude it.
- Existing running instances are not automatically stopped or mutated.
- An operator may block new resolution/download for administrative takedown.
- Published content is not physically deleted through the ordinary MVP API; corrections use a new version.

## Compatibility And Selection

- A producer publishes a structured Target Compatibility Contract: a conjunction of controlled equality/range conditions over a consumer Platform Profile.
- Unknown mandatory conditions fail closed.
- Peer/repository labels are display metadata only.
- The extension runtime adapter filters and deterministically chooses among compatible candidates. Equal candidates may use a stable fallback or optional user override.
- A successful enable binds target key and exact artifact digest. Appending a target never silently changes an existing binding.
- Extension-to-extension dependency graphs are not part of MVP.

## Deployment State And Workflows

### Install

1. The operator selects one exact published Extension Version.
2. Installation records `namespace/name@version` and starts disabled for every peer.
3. Disabled peers require no compatible target or binding.

### Enable On A Peer

1. The peer adapter loads the published version metadata.
2. It evaluates its Platform Profile, selects a compatible target, and binds the exact digest.
3. Only after the target is admitted and initialized successfully is that peer added to the enabled set.
4. Failure leaves the peer disabled and does not change the installed version.

### Disable On A Peer

1. The adapter stops and unloads runtime side effects.
2. It removes only that peer from the enabled set and clears that peer's binding.
3. Other peers and the installed version remain unchanged.

### Uninstall

1. Uninstall is allowed only when the Extension is disabled and non-running on every peer.
2. It removes the deployment installation record, target bindings, and Extension configuration.
3. It does not change Registry publication state.

### Extension Version Change

Version upgrade/rollback orchestration is not required for MVP. The admitted future rule is that only currently enabled peers gate a version change; disabled peers do not. No automatic disable-and-upgrade combined operation is promised.

### Peer Or Runtime Change

An explicitly authorized peer/runtime change has priority over Extension availability. The product discloses affected Extensions and disables incompatible ones only on that peer. Uncontrolled environment drift is outside the MVP promise.

## Availability And Trust Promise

- Registry unavailability does not stop code that is already running.
- New publish, install, enable, or cold-load operations that cannot retrieve their exact artifact fail without changing installed/enabled state.
- Browser targets run with host-page privileges; Python targets run as trusted in-process application code. MVP provides no sandbox.
- MVP integrity is HTTPS plus content digest verification and scoped publisher authentication.
- Malware scanning, signatures, attestations, self-service namespace claims, namespace transfer/disputes, advanced moderation, dependency resolution, mirrors, and offline restart guarantees are explicit non-goals.

## MVP User Journeys

1. An operator manually provisions a namespace and scoped publisher credential.
2. Two independent peer CDs publish different target artifacts into one Extension Version; retries are idempotent and overwrites conflict.
3. The publisher makes that version public; anonymous consumers can read metadata and fetch exact artifacts.
4. A deployment installs the exact version disabled everywhere.
5. `client-web` and `core-py` adapters each resolve, bind, enable, run, and disable their compatible target while observing the same installed version.
6. After both are disabled, the deployment uninstalls the Extension.

Production acceptance uses `inkcre/twitter` if both peer baselines can publish viable targets; a minimal existing first-party target may replace one side only if HLD proves the two implementations are not one coherent Extension product.

## Product Design Exit

The MVP actors, authority, identities, states, workflows, failure behavior, trust promise, and non-goals are accepted. Shared durable product truth will be promoted to the `InKCre/docs` Hub only as part of the later authorized cross-repository integration; this task packet remains the active owner until then.
