# Product Question 04 — Technical Target Contract

## Previous Result

Question 03 established canonical `MAJOR.MINOR.PATCH[-PRERELEASE]` Extension Versions without build metadata. Deployments pin an exact version, while peer Runtime/API compatibility remains separate target metadata.

## Question

Should a Technical Target be an opaque label selected by convention, or a structured compatibility contract that a consumer can evaluate?

**Status**: Structured matching accepted; the three-category condition model below is superseded by Question 05.

## Evidence And Constraint

- Python wheels declare separate Python, ABI, and platform compatibility tags; installers compare those requirements with the running system.
- OCI image indexes attach structured OS, architecture, version, feature, and variant requirements to platform-specific manifests; consumers choose a compatible manifest.
- The current `client-web` target depends on Module Federation plus shared Vue, Pinia, Router, VueUse, Zod, and `@inkcre/core` runtime relationships. The current server extension declares Python 3.12 and imports the in-process Core Extension API. Labels such as `client-web` and `core-py` do not express these compatibility facts.

Sources: [PyPA platform compatibility tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/), [OCI image index](https://github.com/opencontainers/image-spec/blob/main/image-index.md), [Module Federation shared dependencies](https://module-federation.io/configure/shared).

## Alternatives

### A. Opaque Target Label

Publisher and peer agree on strings such as `client-web` or `core-py`. This is easy initially but encodes repository/peer topology, cannot express version ranges, and prevents another compatible peer from reusing the target without special cases.

### B. Exact Full-stack Fingerprint

Encode every browser, framework, library, language, OS, and architecture version. This is mechanically precise but brittle: irrelevant dependency changes create needless target variants and destroy compatibility reuse.

### C. Structured Compatibility Contract

The producer declares only requirements that affect loading and execution; the peer exposes corresponding capabilities. Matching operates on those facts rather than a shared nickname.

## Recommendation

Choose **C: structured compatibility contract**.

The initial proposal distinguished three requirement classes:

1. **Runtime/API contract**: the stable Extension Runtime/API family and compatible version range.
2. **Artifact/integration format**: how the artifact is loaded, such as a Module Federation remote or admitted Python package.
3. **Execution environment**: only compatibility-relevant constraints such as browser/runtime, language/ABI, OS, or architecture.

A peer publishes a consumer capability profile in the same controlled vocabulary. A target matches only when every mandatory requirement is satisfied; an unknown mandatory requirement is incompatible. Human labels may aid display or debugging but never determine compatibility.

Review accepted the structured-over-opaque direction, but rejected these three buckets as an inaccurate fundamental model. In particular, Module Federation both exposes artifact interfaces and requires host-provided loaders/shared modules. Question 05 replaces the buckets with a unified capability/requirement model.

This deliberately does not freeze a schema. Exact dimensions, identifiers, range grammar, matching algorithm, preference ordering, and capability transport belong to HLD and executable contract design.

## Result

Structured, machine-evaluated matching is accepted. The direction and vocabulary of conditions continue in [`05-capability-requirement-model.md`](05-capability-requirement-model.md); target selection remains deferred.
