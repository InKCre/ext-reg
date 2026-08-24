# Registry Control Plane

## Authority Boundary

The Registry owns Extension Name and Nickname, strict-SemVer Release identity
and lifecycle, publisher scope, provenance, and typed associations to native
Python and Module Federation Distributions. Native package metadata remains
owned by its ecosystem. Deployment installation, Peer enablement, and runtime
activity are not Registry state.

There is deliberately no generic target manifest, cross-format artifact, or
Registry-owned compatibility predicate. One Release may independently append
one Python association and one Module Federation association; either is
optional. Association metadata, filenames, and bytes are immutable. Identical
retries are idempotent; conflicts require a new Release.

`preparing` is private and publication requires at least one admitted native
Distribution. `published` and `yanked` preserve descriptors and bytes;
`blocked` is a separate operator read-denial state.

## Native Admission and Reads

The Python surface admits bounded wheel uploads through `/legacy/`, validates
the declared digest, filename, normalized project, version congruence, Core
Metadata, entry point, and archive safety, then exposes PEP 503/691 and PEP 658
projections through `/simple/` and `/packages/`. The request is declared-length
and capped at 20 MiB because Python Workers cannot use Starlette's normal
thread-backed spill path.

The Module Federation surface admits a bounded ZIP rooted at
`mf-manifest.json`, validates its relative Remote entry and referenced assets,
and materializes only the manifest's public path from canonical
`PUBLIC_ORIGIN`. It does not mint a second public manifest schema.

The generated [OpenAPI contract](../../contracts/openapi.json), JSON Schemas,
models, routes, generated contracts, and build checks are the exact executable interface authorities.

## Persistence and Security

D1 owns identity, lifecycle, association metadata, and hashed namespace
credentials. R2 owns immutable private bytes. Admission writes staging bytes
before a conditional D1 exposure transition; unreachable staging objects are
recoverable garbage, never public authority. Every raw-byte read first proves
a readable D1 association.

Raw credentials never enter D1 or evidence. Anonymous reads are limited to
published or yanked state. Registry admission validates structure and
integrity, not publisher trust: Python code executes in a trusted Core process
and a Module Federation Remote receives host-page privileges. Platform Hosts
must perform their own compatibility and runtime negotiation before execution.
