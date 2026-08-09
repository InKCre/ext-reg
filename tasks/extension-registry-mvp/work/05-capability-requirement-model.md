# Product Question 05 — Target Compatibility Predicate

## Previous Result

Question 04 accepted machine-evaluated target matching and rejected `client-web`/`core-py` as compatibility authority. The initial three-category taxonomy was rejected as overlapping and incomplete.

## Question

Can artifact/integration facts and execution-environment requirements be reduced to one producer-authored predicate over a consumer platform profile?

**Status**: Accepted.

## Correction To The Previous Recommendation

The previous bilateral `provides`/`requires` model exposed internal symmetry that the Registry product does not need. An artifact format, Extension API implementation, entry point, host dependency, and Web/Python execution constraint all answer one product question: **can this target be loaded and executed by this platform?**

Model that question directly:

```text
compatible(target, platform) := target.compatibility(platform) == true
```

- The **producer** publishes one structured Target Compatibility Contract: a machine-evaluated predicate over the platform on which its artifact can be installed.
- The **consumer** supplies a Platform Profile containing actual facilities and the integration contracts it accepts.
- The deployment evaluates the predicate for every participating peer. Any unknown or unsatisfied mandatory condition fails closed.

There is no public product-level need for targets and peers to be symmetric resources or to expose top-level `provides`/`requires` collections.

## Module Federation Example

A web target can constrain its compatible platform to one that:

- accepts the target's Module Federation remote format and format-contract version;
- accepts the Extension lifecycle/API version implemented by the target;
- supplies an MF loader and the named share scope;
- supplies compatible shared modules such as Vue and `@inkcre/core` when the target does not bundle them;
- supports the JavaScript syntax and Web Platform features used by the emitted artifact.

The target's Module Federation format, lifecycle implementation, and required conventional entry point are artifact facts, but for installation they compile into platform-acceptance conditions. Arbitrary extension-specific `exposes` describe extension functionality; they are compatibility conditions only when an accepted Runtime/API contract requires those entry points.

Module Federation documents `library.type` as the container output format, `exposes` as producer modules, and `shared` as runtime negotiation including `requiredVersion`, `shareScope`, `import: false`, and `shareKey`. In particular, `import: false` requires the consumer to supply the shared module. Sources: [library format](https://module-federation.io/configure/library), [exposes](https://module-federation.io/configure/exposes), [shared dependencies](https://module-federation.io/configure/shared).

Do not equate a bundler/plugin package version with a stable Module Federation integration-contract version unless that implementation explicitly guarantees the mapping. The contract needs an accepted load format and conformance evidence, not merely `@module-federation/* >= X`.

## Web Execution Constraint

`V8` alone is insufficient: it is Chrome's JavaScript/WebAssembly engine, while a browser target may also depend on Blink/Web standards such as DOM, CSS, Fetch, ESM loading, and browser security policy. `Chrome` is usable as a display or deployment fact but is too coarse as the canonical condition.

Prefer an explicit Web execution baseline plus separately named non-baseline Web features. Browser name/version can be an adapter input from which a consumer derives that profile. The current Twitter target uses Vite `build.target: 'esnext'`; Vite defines this as native dynamic import with minimal transpilation, so it does not establish a durable minimum browser version. A future HLD must replace or supplement this with an explicit build baseline and conformance checks. Sources: [Chrome rendering and V8](https://developer.chrome.com/docs/web-platform/blink), [Vite build target](https://vite.dev/config/build-options), [Web Platform Baseline](https://developer.mozilla.org/en-US/docs/Glossary/Baseline/Compatibility).

## Recommendation

Accept a single **Target Compatibility Contract → Platform Profile** match:

- compatibility is a producer-authored, structured predicate, not an opaque `compatible-with` label;
- the consumer profile combines detected environment facts with the integration contracts that the peer accepts;
- environment, loader, artifact format, Runtime/API, shared modules, language/ABI, OS, and architecture are namespaced condition dimensions only when they materially affect loading or execution;
- human labels remain display/debug metadata;
- exact vocabulary, predicate grammar, profile discovery, derivation from build metadata, and matching implementation remain HLD/contract work.

## Result

The one-direction Target Compatibility Contract model is accepted. Selection and binding stability among several compatible targets continue in Question 06.
