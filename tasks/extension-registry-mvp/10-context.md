# Context And Evidence

## Purpose

Keep evidence-backed current reality separate from decisions, proposed architecture, execution sequencing, and acceptance claims.

## Product Truth

- InKCre Extension Registry is a public extension/package hosting service analogous in role to npm Registry or PyPI, not only an internal InKCre catalog.
- The service supports multiple publishers and owns the production publication, discovery, resolution, and download surface for admitted packages.
- Extension source remains in publisher-owned repositories. First-party source remains in the relevant peer repositories and publishes through peer-owned CD.
- First-party packages use a reserved InKCre namespace but otherwise follow the same Registry contracts and publication path as third-party packages.
- All participating peers connect to the same deployment database and must observe one installed version for a given extension.
- Peers consume extension artifacts according to technical runtime compatibility; a Chrome + Vue.js + Module Federation peer is one concrete target shape.
- An extension is an installable capability that can add bounded source, resolver, storage, sink, or protocol behavior. It is not merely a Python package or frontend bundle.
- Extension capabilities enter a peer through controlled registration and lifecycle hooks; they must not bypass info-base graph authority or deployment ownership boundaries.
- `installed`, `enabled`, and `running` are distinct states:
  - `installed`: the deployment has the extension package and persisted installation record;
  - `enabled`: a particular peer/client is permitted to run it;
  - `running`: the current runtime has started it and applied its side effects.
- The Registry must not become the authority for those deployment/runtime states.

## Peer Reality

### core-py

- Extensions are trusted in-process Python capabilities embedded into the application artifact.
- Discovery imports `extensions.<id>.Extension` from an artifact-local directory.
- The runtime deliberately does not download arbitrary extension code.
- The persisted extension row does not contain registry origin, artifact digest, publisher, target components, or target compatibility.

### client-web

- Extensions are Module Federation remotes running with host-page privileges.
- The current load path is `<registry-url>/<extension-id>/client-web/remoteEntry.js?version=<version>`.
- Discovery lists deployment-installed database rows; it does not query a Registry catalog.
- The current runtime has no admitted manifest, signature, artifact digest, publisher, or compatibility contract.

### Cross-peer Identity Gap

- Product direction now requires one Extension Version to contain multiple technical targets so all peers sharing the database preserve one installed version.
- Because each peer owns and publishes its target artifact independently, package identity, target identity, append authorization, upload conflicts, and deployment compatibility semantics still require explicit product design.
- The existing database version field must not be overloaded with Registry artifact identity before that meaning is designed and proven.

## Repository Initialization Evidence

- The pre-initialization record contained 137 lines with SHA-256 `4a31b0dbd32c5bc0b2781589b8aaca2c44e692736ebb6754b1dfc87ff574a258` before migration into the task packet.
- Git was initialized on branch `main` with no commits.
- SVC initialization applied plan digest `dfab4f76931438a7b703ff66ffd3a1d068c43777793c5b0fd36b10e117a06585` for SVC 11.0.1 and passed its built-in verification.
- Final initialization verification reported SVC `healthy: true`, repeat init `status: noop`, valid `svc.json`, the expected repository control files, no root pre-initialization file, and no trailing whitespace.

## Primary Evidence Owners

- Shared product truth and cross-unit contracts: sibling `InKCre/docs` repository.
- Python runtime mechanics and security boundary: sibling `InKCre/core-py` repository.
- Browser runtime, Module Federation, and client delivery mechanics: sibling `InKCre/client-web` repository.
- Registry task decisions and active uncertainty: this task directory.
