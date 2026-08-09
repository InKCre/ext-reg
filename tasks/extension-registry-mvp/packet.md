# Extension Registry MVP

- **Objective**: Develop the public InKCre Extension Registry through a production-accepted MVP: a multi-publisher extension/package hosting service analogous in role to npm Registry or PyPI, with stable Extension Runtime/API distribution and coherent publisher-to-consumer workflows.
- **Guardrails**: Finish HLD, implementation planning, and written preflight before executable implementation; use fresh `origin/main` feat worktrees for both peers; preserve separate Registry/installed/enabled/running authority; keep Python target admission trusted and deployment-controlled; prefer mature libraries/standards; limit automated tests to a few critical black-box E2E paths; do not build non-MVP dependency, security, moderation, or edge-case systems.
- **Verification**: Pass the bounded gates in [`50-acceptance.md`](50-acceptance.md), ending with both peer CDs publishing to public Registry production and a real shared-database install → per-peer enable/run → disable → uninstall journey.
- **Current Truth**: The production MVP is accepted. Product design, HLD, targeted PoCs, Registry implementation and delivery, both peer integrations, Runtime/API `0.1.3`, and the real shared-database lifecycle journey are complete. Production proved one exact `inkcre/twitter@0.1.0` installation selecting different immutable Web and Core targets, Web cold restore, both peer disables, Core route withdrawal, uninstall, and zero installation/binding/route residue.
- **Next Step**: Close this MVP packet. Treat legacy `extensions` migration and every excluded capability as separate post-MVP product work rather than extending this accepted scope.

## Supporting Material

- [Context and evidence](10-context.md): product truth, peer reality, identity gaps, and initialization evidence.
- [Product design working model](15-product-design.md): actors, product concepts, invariants, workflows, open questions, and the exit gate before HLD.
- [Decisions](20-decisions.md): accepted, provisional, and open task decisions, including source ownership and Python-first direction.
- [High-level technical design](30-architecture.md): admitted topology, contracts, data model, peer admission, failure behavior, and production boundary.
- [Roadmap and work structure](40-roadmap.md): corrected phase order, future execution-file convention, and unresolved choices.
- [Acceptance model](50-acceptance.md): staged product design, HLD, PoC, initialization, CI/CD, contract, peer, and production gates.
- [Completed question 01](work/01-version-publication.md): accepted version publication and deployment-relative target coverage behavior.
- [Completed question 02](work/02-package-coordinate.md): accepted mandatory namespaced Extension coordinate.
- [Completed question 03](work/03-version-scheme.md): accepted strict SemVer profile and exact installed-version pinning.
- [Completed question 04](work/04-target-contract.md): accepted structured matching over opaque target labels; initial taxonomy superseded.
- [Completed question 05](work/05-capability-requirement-model.md): accepted one-direction target-to-platform compatibility semantics.
- [Completed question 06](work/06-target-selection.md): accepted adapter-owned stable selection and exact target/digest binding.
- [Completed question 07](work/07-platform-change.md): accepted impact disclosure and per-peer disablement during authorized platform changes.
- [Completed question 08](work/08-compatibility-gates.md): accepted enablement-scoped compatibility gates and excluded Extension dependencies from MVP.
- [Completed HLD PoCs](work/09-hld-pocs.md): production Python Worker/D1/R2 and cross-origin relative Module Federation artifact evidence.
- [Implementation plan](work/10-implementation-plan.md): exact files, contracts, migrations, workflows, merge order, and production resources across all three repositories.
- [Pre-implementation rehearsal](work/11-preflight.md): publication races, lifecycle compensation, delivery ordering, secrets, outage, integrity, and rollback simulation.
- [Registry implementation](work/12-registry-implementation.md): executable foundation, quality gates, Worker-runtime corrections, and black-box evidence.
- [Production delivery](work/13-production-delivery.md): remote/release identity, Cloudflare resources, delivery failures, runtime isolation, and public smoke evidence.
- [Peer integration](work/14-peer-integration.md): fresh worktree identities, Runtime/API compatibility corrections, cross-repository execution state, and final production journey evidence.
