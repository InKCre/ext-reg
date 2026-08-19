# Final Review Findings — Runtime alignment

- **Status:** accepted; no blocker/high finding
- **Authority:** D043
- **Supersedes:** readiness conclusions in `82`
- **Evidence:** `78`, `80`, `83`, current ext-reg package manifests and current
  Core/Client feature worktrees

## Findings and Resolutions

### 1. Repository abstraction duplicated the established model

`ExtensionStore`/`SQLExtensionStore` was introduced during native cutover and
owns the whole relation despite living in `state.py`. It is not a historical
Core convention and is not required by the accepted dependency direction.

**Resolution:** restore `ExtensionModel` as the rich Active Record for the
whole row. Runtime `ExtensionManager` uses it directly; `ExtensionBase` binds
the active model. Runtime performs no raw SQL and does not own migrations.

### 2. Manager/Base ownership was split across two authorities

The first extraction plan moved native loading but left `ExtensionManager` and
`ExtensionBase` lifecycle in Core. That would leave Runtime too thin and keep
the defective sequencing in the Peer.

**Resolution:** the per-Peer Runtime owns manager, base/module lifecycle,
native consumer and compensation. Core/Client lower layers own their rich model
and concrete Peer APIs; application composition imports the Runtime afterward.

### 3. Generic Ports reproduced architecture without product value

Persistence and Contribution Ports would hide concrete Peer APIs that an
Extension is already allowed to use and would create a second compatibility
surface.

**Resolution:** no generic Port framework. Core Runtime uses concrete
Core model/contribution APIs. Web Runtime uses the concrete Client model and
the mature Module Federation Host API supplied by the application composition.

### 4. Shared contracts could drift across three release units

Handwritten Python Pydantic and Web Zod models would become independent
authorities.

**Resolution:** Registry-owned Pydantic/FastAPI source emits checked OpenAPI
3.1/JSON Schema. `datamodel-code-generator` generates Python consumer models;
`@hey-api/openapi-ts` with fetch and Zod v4 plugins generates Web bindings.
Repository checks regenerate and fail on a dirty diff.

### 5. Toolkit risked becoming a build-system abstraction

Building arbitrary producer projects inside Toolkit would duplicate PEP 517
and package-manager behavior.

**Resolution:** producers build normally. Toolkit finalizes one existing wheel
with the installed Extension metadata record, repacks it through the supported
`wheel` library happy path, then inspects it.

### 6. Preview validation previously optimized the wrong boundary

Full-tree reads, byte comparisons, cache workarounds and long retries consumed
runner time without improving the setup slice.

**Resolution:** ordinary repository checks plus provider deployment success and
short semantic black-box journeys. No artifact-wide public verification.

### 7. Core Runtime is intentionally not a standalone library

Final review correctly observed that the Runtime imports Host-provided `app.*`
modules while Core composition imports the Runtime package. Turning that into a
generic adapter would contradict D043 and recreate the rejected Port layer.

**Resolution:** define this explicitly as a host-provided import contract, not a
package-manager dependency. `core-py` is the executable host, not a dependency
published for Runtime to install. Lower Core model/API modules never import
Runtime, so Python's module graph is acyclic. Runtime release readiness includes
an integration install/import/lifecycle check in a compatible Core source tree;
standalone execution without Core is neither promised nor tested. The Web
package follows the native npm equivalent through a peer dependency on
`@inkcre/core` and a packed-consumer integration check.

## Review Verdict

No product or architecture question remains. The initial final review's one
high finding is resolved by making the deliberate host-provided dependency and
consumer integration release gate explicit, without introducing an adapter.
The confirmation review accepted the revised dependency and publication
sequence with no blocker/high finding. Its remaining command-level suggestions
are incorporated in the active plan.
