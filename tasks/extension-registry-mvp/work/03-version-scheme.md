# Product Question 03 — Extension Version Scheme

## Previous Result

Question 02 established mandatory `namespace/name` as the public Extension coordinate. Version, technical target, ecosystem package name, and artifact digest remain subordinate identities.

## Question

What version syntax and installation-reference semantics should govern a language-neutral, multi-target Extension Version?

**Status**: Accepted.

## Evidence And Constraint

- SemVer 2.0.0 defines `MAJOR.MINOR.PATCH`, ordered pre-release identifiers, and build metadata that is ignored for precedence. It requires released package contents not to be modified under the same version.
- npm expects semver-compatible package versions and resolves dependency ranges using SemVer behavior.
- PEP 440 supports Python-specific epochs, post/dev releases, local versions, and multiple normalized spellings. Those features are useful inside Python packaging but would make the Registry's cross-Python/JavaScript product identity more complex.
- Existing first-party server and web extension packages already use `0.1.0`, and the shared database currently stores an exact version-like string.

Sources: [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html), [npm semantic versioning](https://docs.npmjs.com/about-semantic-versioning), [PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/).

## Alternatives

### A. Opaque Version String

Accept any publisher-supplied version. This maximizes ecosystem compatibility but prevents deterministic ordering, range resolution, and coherent upgrade UX.

### B. PEP 440

Adopt Python's richer version model. This fits the preferred Registry implementation language but incorrectly makes Python packaging semantics the public cross-peer contract.

### C. Strict SemVer 2.0.0

Use one language-neutral version grammar understood by both Python and JavaScript tooling. Keep peer compatibility and exact artifact identity outside the product version.

## Recommendation

Choose **C: strict SemVer 2.0.0**, narrowed for canonical public identity:

- canonical `MAJOR.MINOR.PATCH[-PRERELEASE]` only;
- no leading `v`;
- allow pre-releases such as `1.2.0-rc.1`;
- disallow `+BUILD` metadata because artifact digest and provenance already identify builds, while SemVer ignores build metadata for precedence;
- store an exact version such as `1.2.0` in deployment installation state, never a range or moving label;
- exclude pre-releases from ordinary stable selection unless explicitly requested.

SemVer communicates changes to the Extension's public product/API behavior. It does **not** prove that a peer Runtime/API is compatible; that remains target-level metadata and deployment preflight.

Appending a new target to a published version is allowed only because it adds a distribution implementation of the same product semantics. Changing observable Extension behavior still requires a new Extension Version.

## Result

Strict SemVer without build metadata and exact installed-version pinning are accepted. Version ranges, moving release channels, compatibility grammar, and `0.x` policy remain deferred.
