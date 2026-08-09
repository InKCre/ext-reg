# Product Question 02 — Public Extension Coordinate

## Previous Result

Question 01 established that an Extension Version has no required-target set. It is a public, append-only collection of immutable target artifacts, while each deployment owns compatibility coverage before install or upgrade.

## Question

What is the canonical public identity of an Extension, and should version or technical target be part of that package coordinate?

**Status**: Accepted.

## Evidence

- npm uses `@scope/name`: the scope is a user or organization namespace controlling who may publish packages within it.
- PyPI uses a flat project namespace and normalizes case plus `.`, `_`, and `-` runs to one form, demonstrating the collision and aliasing rules a flat public name requires.
- OCI separates repository name from tag or digest; content variants and exact bytes do not become repository identity.
- InKCre already has several names for the same first-party source: local extension ID `twitter`, Python project `inkcre-ext-twitter`, and npm project `@inkcre/ext-twitter`. None is currently a cross-peer product coordinate.

Sources: [npm scopes](https://docs.npmjs.com/using-npm/scope.html/), [PyPA name normalization](https://packaging.python.org/en/latest/specifications/name-normalization/), [OCI Distribution definitions](https://github.com/opencontainers/distribution-spec/blob/main/spec.md#definitions).

## Alternatives

### A. Flat Global Name

Use `twitter` as the public Extension identity. This is short but creates global name squatting, weak publisher ownership signaling, and special handling for the reserved first-party namespace.

### B. Mandatory `namespace/name`

Use `inkcre/twitter` as the first-party example and require the same two-part shape for every publisher. Namespace ownership governs publication; the name identifies one Extension within it.

### C. Put Target In The Package Coordinate

Use identities such as `inkcre/twitter/client-web`. This makes each technical target look like a separate installable Extension and conflicts with the accepted rule that one Extension Version contains several targets under one shared installed version.

## Recommendation

Choose **B: mandatory `namespace/name`** with these identity layers:

| Layer | Example | Meaning |
| --- | --- | --- |
| Extension | `inkcre/twitter` | Stable public product identity |
| Extension Version | `inkcre/twitter@0.1.0` | One shared deployment version; exact version grammar is a later question |
| Technical Target | a target identity within that version | Runtime-compatible variant, not a package |
| Target Artifact | target identity plus digest | Exact immutable bytes |

Canonical namespace and name segments should be lowercase ASCII slugs. `inkcre` is reserved for first-party Extensions. The leading `@` used by npm should not be part of InKCre's canonical identity; it is ecosystem-specific syntax rather than product meaning.

Peer-local IDs and build-package names remain adapter inputs. For example, local `twitter`, Python `inkcre-ext-twitter`, and npm `@inkcre/ext-twitter` may all publish to or consume `inkcre/twitter` without becoming aliases in the public Registry.

## Result

The mandatory `namespace/name` coordinate and the rule that version and target remain subordinate identities are accepted. Exact slug grammar, version grammar, target identity, aliases, transfers, and legacy migration remain deferred.
