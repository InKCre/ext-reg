# Product Question 06 — Target Selection And Binding Stability

## Previous Result

Question 05 accepted a producer-authored Target Compatibility Contract evaluated against a consumer Platform Profile. Compatibility is a one-direction predicate; opaque peer labels and the superseded bilateral resource model are not selection authority.

## Question

When several targets in one Extension Version are compatible with the same peer, who selects one, and may a later target append silently change the artifact used by an installed deployment?

**Status**: Accepted with the equal-candidate refinement below.

## Product Constraints

- One Extension Version may contain overlapping compatible targets.
- A public version may gain distinct targets after installation, while every accepted target artifact remains immutable.
- The Registry cannot know a deployment's format, security, performance, or fallback preferences better than its consumer adapter.
- Reusing the same installed version must not silently introduce different executable bytes.

## Evidence

Python packaging computes an ordered list of tags supported by the running interpreter, with the best match first. This makes preference consumer-derived rather than package-upload order. The OCI Image Index instead recommends the first matching manifest, but that order belongs to one index; copying it into an appendable Registry collection would make insertion order a hidden compatibility policy. Sources: [Python platform tags](https://packaging.pypa.io/en/latest/tags.html), [OCI Image Index](https://github.com/opencontainers/image-spec/blob/main/image-index.md).

Python's accepted lock-file specification requires installers to choose an appropriate recorded wheel offline, reject conflicting ambiguity, and validate the selected file's size and hash. This supports separating resolution from repeatable execution. Source: [PEP 751](https://peps.python.org/pep-0751/).

## Alternatives

### Publisher Or Registry Order

Choose target priority, upload order, catalog order, or first match. This is simple but assigns platform preference to the wrong authority. Appending a target can also change future resolution under an unchanged Extension Version.

### Generic `most specific` Ranking

Prefer the target whose predicate is narrower. Compatibility predicates can be incomparable, and greater specificity does not universally mean safer or better. This cannot be the generic product rule.

### Consumer Preference Plus Exact Binding — Accepted

1. The deployment filters targets by the accepted compatibility predicate.
2. The peer/runtime adapter applies a deterministic, auditable preference policy for its own platform.
3. If several candidates remain equally preferred, the adapter chooses one by a documented stable fallback. It may optionally expose those compatible candidates for an operator/user override; ordinary non-interactive installation does not require a user decision.
4. A successful deployment plan records the chosen target identity and artifact digest for each participating resolution subject, subordinate to the one shared Extension Version.
5. Restart and download use that exact binding. Appending another compatible target does not change an existing installation.
6. Adopting another target requires an explicit re-resolution event; exact triggers and persistence representation remain later product/HLD work.

The consumer policy can prefer, for example, an accepted native artifact over a portable fallback or a preferred load format over another accepted format. Compatibility overlap is normal—such as a newer Windows platform satisfying a target that also runs on an older Windows generation—and is not itself an error. The Registry validates and returns candidates but does not invent this preference.

## Result

Consumer-owned deterministic selection and exact target/digest binding are accepted. Equal compatible candidates use a stable arbitrary fallback rather than failing; optional user choice may override the default before binding. This preserves deployment reproducibility without changing the invariant that all peers share one Extension Version.

The exact fallback order and override UX remain HLD/peer-adapter concerns rather than Registry product policy.

Behavior when a participating peer is added or its Platform Profile changes continues in Question 07.
