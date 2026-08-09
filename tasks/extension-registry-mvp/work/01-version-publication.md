# Product Question 01 — Version Publication Boundary

## Question

When several peer-owned CD pipelines independently upload target artifacts for one Extension Version, when does that version become publicly discoverable and installable?

**Status**: Accepted with the MVP refinement below.

## Constraints Already Accepted

- One deployment installs one Extension Version shared by all peers connected to its database.
- That version may contain different target artifacts for different technical runtime contracts.
- Target artifacts arrive independently from publisher-owned repositories and CD pipelines.
- A consumer must not observe different artifact content for the same target identity under the same published version over time.

## External Product Evidence

- npm staged publishing separates a non-public staged package from an explicit approval that publishes it.
- npm treats a package name and version as immutable identity: the same name and version cannot later be republished, including after unpublish.
- PyPI models one release as one version with one or more distribution files, but its upload API creates the release when the first file arrives and accepts later files. This is useful evidence for multi-artifact releases, but exposes a progressive-completeness model.

Sources: [npm staged publishing](https://docs.npmjs.com/staged-publishing/), [npm unpublish policy](https://docs.npmjs.com/policies/unpublish/), [PyPI help](https://pypi.org/help/), [PyPI upload API](https://docs.pypi.org/api/upload/).

## Accepted Decision

- The Registry does not define or validate a version-level set of required targets. There is no producer-independent meaning of a globally complete Extension Version.
- An authorized publisher may explicitly publish an Extension Version after at least one target artifact has been accepted.
- A published version may gain new, distinct target artifacts over time so independently operating peer CDs do not need a synchronized release run.
- An accepted target identity and artifact digest are immutable. A publisher may append a new target, but may not replace an existing target's bytes under the same Extension Version.
- Target coverage is deployment-relative. Before install or upgrade, the deployment must prove that every participating peer can resolve a compatible target from the selected Extension Version. Otherwise it rejects the operation without changing the installed version.

Explicit publication remains useful as the publisher-controlled transition from private preparation to public visibility, but it is not a completeness certification.

## Why

Only a deployment knows which peers participate and which technical stacks they must satisfy. Asking the producer or Registry to declare required targets would either encode one deployment topology as universal policy or create release coordination with no reliable authority behind it.

This deliberately differs from the earlier recommendation to freeze the entire target set at publication. The stable unit is now each target artifact, while the Extension Version is an append-only collection of those immutable targets.

## Observable Behavior

1. A privately preparing version is not returned by public discovery or installation resolution.
2. Once it contains at least one accepted target, an authorized publisher may make it public.
3. A new target may later be appended to that public version; an existing target identity cannot be overwritten.
4. Public discovery may show a version that is unsuitable for a particular deployment. That is a valid version, not an incomplete Registry object.
5. Install and upgrade perform deployment-wide target preflight before mutating the shared installed version.

Exact state names, participating-peer scope, target identity and overlap rules, upload idempotency, checks, yank/revoke, and failure recovery are deferred to later single-question discussions.
