# HLD 5 — Versions, Repositories and Delivery

## Version Plan

Use versions as the pre-download Host SDK capability gate; do not reintroduce
generic capability labels:

| Product | Current | Setup release |
| --- | --- | --- |
| Core service / Core Python Host SDK | `0.1.0` | `0.1.1` |
| `@inkcre/core` Web Host SDK | `0.1.0` | `0.1.1` |
| `inkcre/twitter` Extension Release | `0.1.1` | `0.2.0` |

The Twitter Python and Module Federation Distributions both use Extension
version `0.2.0`. Their Host associations require their respective SDK
`>=0.1.1 <0.2.0`. Other existing Python Extensions keep
`>=0.1.0 <0.2.0` and remain compatible with Core `0.1.1`.

A read-only production Registry probe on 2026-08-13 confirmed that
`inkcre/twitter@0.1.1` is published with both native associations and
`inkcre/twitter@0.2.0` returns 404. The chosen immutable Release identity is
therefore currently available; the probe performed no Registry mutation. Repeat
that exact read-only lookup before final PR handoff. If another actor has since
occupied `0.2.0`, stop and review a new cross-format version rather than
overwriting or silently bumping one Distribution.

## Repository Ownership

### `core-py`

Owns:

- the additive `extensions.state` migration and database contract v3;
- Core state transactions and direct-write restrictions;
- typed Core Host state APIs and exact public-route lifecycle;
- request-log redaction;
- Twitter Python setup/OAuth/Source protocol and wheel `0.2.0`;
- Core/Authlib/HTTPX dependency baseline and frozen lock;
- Python, migration, PostgreSQL and wheel verification.

### `client-web`

Owns:

- Web Host setup contribution and `@inkcre/core 0.1.1`;
- Extension-card action and `InkDialog` shell;
- Twitter Web wizard and native MF Distribution `0.2.0`;
- database contract generated from the exact Core branch image;
- Vue/Host/component tests and native MF closure/build checks.

### `ext-reg`

Needs no source change. Its native Release already supports independently
published Python and Module Federation associations under the same Extension
name/version. This task packet is the only Registry-repository mutation for this
planning phase.

## Existing CD Happy Path

No new publisher workflow is required:

- Core's `extension-publish.yml` detects the changed Twitter subtree, builds and
  verifies the wheel, prepares the native Python association, uploads through
  `/legacy/`, and publishes/reads back the exact Release.
- Client's checked-main delivery uploads the exact Twitter MF artifact, prepares
  the native Module Federation association, publishes it and verifies its
  Registry-hosted manifest/assets before Pages delivery.
- Registry permits the second native association to append to an already
  published immutable Release, so merge order does not change Extension
  identity. Operationally Core should merge/publish first, then Client, so the
  wizard is not visible before a Core setup endpoint can exist.

This implementation task stops before either workflow can run on `main`.
Publishing, deployment and black-box acceptance remain outside the authorized
boundary.

## Cross-repository Contract Synchronization

The Client PR must not hand-edit generated database truth or wait for a merge.
Use the already configured SSH Docker provider:

1. build and start an exact Core feature-branch development image with
   `scripts/dev_database.py ensure <task-instance>`;
2. record its local daemon tag and source revision;
3. point Client's checked SSH provider at the same Docker daemon;
4. run `pnpm contract:sync -- --image <exact-development-tag>`;
5. immediately run `pnpm contract:check -- --image <same-tag>`;
6. stop the task-owned runtime after evidence is captured.

`scripts/dev_database.py stop` removes the exact Compose project, volume, local
state and tunnel. The development image tag is source-revision-scoped rather
than instance-owned and may be reused by another task, so this plan neither
deletes it nor runs broad Docker prune operations.

The machine has no local Docker CLI, but the configured SSH target and remote
Docker provider are available and have already supported this repository's
database-contract workflow. This is therefore an implementation step, not an
unresolved environment question.

## PR Shape

Prepare two new branches and two new PRs:

1. **Core PR** — state authority, callback ingress, Twitter Python setup and
   version/dependency changes. It is independently reviewable and fully green.
2. **Client PR** — exact generated v3 contract, Host contribution, popup shell,
   Twitter wizard/MF `0.2.0`. It declares the Core PR as a dependency but uses
   the exact unmerged Core branch image for generated evidence.

Both PRs stop ready for review, but not with the same merge status. Core is a
normal independently green PR. Client is opened as Draft/reviewable and is
explicitly merge-blocked until Core lands. Client's GitHub `workspace` and E2E
checks intentionally resolve the protected `stable` Core image and therefore
remain an expected dependency gate while stable is still contract v2; the plan
does not weaken those workflows or add a feature-image bypass. Local exact
feature-image checks are attached as review evidence only. After Core is
admitted, Client must regenerate/check against that admitted Core revision
before becoming merge-ready. Do not merge, publish, release or deploy. Do not
open an ext-reg source PR unless implementation discovers an actual Registry
contract defect; the completed investigation has found none.
