# Extension Developer Toolkit

`inkcre-extension-toolkit` is an independent developer/CD distribution. Its
base package owns pure, Registry-compatible native association projections;
the `cli` extra owns HTTP and command dependencies and exposes `inkcre-ext`.
The Registry service may reuse the pure library, but the Toolkit must not
depend on Registry implementation or Worker runtime state.

The Toolkit prepares Release descriptors, uploads native Module Federation
snapshots, and builds deterministic static preview facades from one explicit,
language-neutral inventory. A facade may contain multiple Extensions and only
the supplied native associations. It rejects Release and path collisions and
reuses the same Registry-owned projection functions for Simple API, wheel,
metadata, Release, manifest, and asset paths.

The Toolkit is not a Registry service or Host SDK. It does not own deployment
installation, Peer enablement, runtime activation, or Extension business
behavior. Package metadata in `toolkit/pyproject.toml`, generated schemas,
source, generated contracts, and build checks are executable authority for its released interface.
