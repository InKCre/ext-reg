# Extension Registry GitHub Governance Alignment

- **Objective**: Bring `InKCre/ext-reg` Git and GitHub delivery authority into
  explicit alignment with the organization governance baseline, and establish a
  useful PR-review evidence model for the read-only Extension-list UI that is
  feasible without paid per-PR infrastructure.
- **Guardrails**: Treat the current audit as evidence, not permission to mutate
  repository settings, organization policy, secrets, workflows, or Cloudflare;
  do not merge the pending preview-cleanup workflow as-is; never expose
  production authority to candidate PR code; do not mutate a persistent shared
  staging data plane from PR validation; keep production delivery and
  `registry.inkcre.dev` available; require a separate impact handshake for the
  cross-repository `.github` scope change; assume zero incremental recurring
  preview cost until objective quota evidence proves otherwise; do not promise
  an interactive Registry API, publisher journey, installation journey, or
  runtime integration from PR Preview; prefer artifact evidence or no remote
  preview over a misleading or under-governed public URL.
- **Verification**: Organization scope and repository profile explicitly cover
  `ext-reg`; live repository settings, required contexts, merge policy, Actions
  token permissions, Environments, credentials, workflow authorities, PR
  evidence, cleanup, and concurrency match that profile; candidate PR code has
  no production-capable credential; preview cost and quota assumptions are
  measured; the accepted preview journey is proven from candidate head through
  retirement without production mutation or residue; independent automated
  black-box checks continue to prove Registry API and native distribution
  behavior.
- **Current Truth**: The governance and static-Preview cutover is accepted and
  live. `InKCre/.github` formally covers `ext-reg`; protected `main`, Actions
  defaults, external-contributor approval, merge policy, and protected Preview
  and production Environments match the accepted profile. Candidate PR code is
  secret-free. One fixed Pages Direct Upload project receives only the bounded
  UI artifact through trusted default-branch controllers and dedicated
  Pages-only authority. The two-head canary proved exact-head replacement,
  stale-head rejection, close tombstones, and deletion of older exact-branch
  deployments. A separate least-privilege production token passed the read-only
  production verify, after which `ext-reg` was removed from the shared
  organization Cloudflare secret. The obsolete shared Preview D1/R2 resources
  and variables were deleted after the rollback window. `registry.inkcre.dev`
  continues to serve the Web UI, six Extension releases, Simple API 1.1, and
  native distribution paths. Full local contracts and the final live-settings
  audit pass. Detailed evidence is recorded in the black-box acceptance report.
- **Next Step**: No implementation or control-plane work remains in this task.
  Preserve the latest PR tombstones as policy-owned audit records and follow the
  normal governance workflow for future changes.

## Supporting Material

- [Context and live evidence](00-context.md)
- [Governance findings](10-findings.md)
- [Decisions](20-decisions.md)
- [Free-preview option frame](30-preview-options.md)
- [Roadmap](40-roadmap.md)
- [Acceptance gates](50-acceptance.md)
- [Whole-plan review](60-plan-review.md)
- [Evidence-form and free-tier investigation](70-evidence-form-investigation.md)
- [Governance and static Preview HLD](80-governance-preview-hld.md)
- [Implementation-ready plan](90-implementation-plan.md)
- [Replacement whole-plan review](95-whole-plan-review.md)
- [Independent overdesign review](96-overdesign-review.md)
- [Simplified-plan independent review](97-simplified-plan-review.md)
- [Local implementation evidence](98-local-implementation-evidence.md)
- [Black-box acceptance and cleanup evidence](99-black-box-acceptance.md)
