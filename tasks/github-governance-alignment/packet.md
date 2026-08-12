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
- **Current Truth**: The protected-main baseline is mostly present, but `ext-reg`
  is absent from the formal organization enforcement scope. Live settings still
  allow merge commits, grant write-by-default Actions tokens, allow Actions to
  approve PRs, and leave `production` unrestricted. The default-branch Preview
  lane still runs candidate workflow code with the production-capable
  Cloudflare token and mutates one shared preview D1 until a reviewed change is
  merged. Sir accepted one fixed preview-only Pages Direct Upload project with
  deterministic same-repository PR branches and artifact-only evidence for
  forks. GitHub's maintainer-approval policy, not a custom HTML/CSS validator,
  is the untrusted-code gate. After the simplified plan passed independent
  review, Sir explicitly authorized the ext-reg-local implementation. The
  worktree now replaces the abandoned per-PR Worker/data-plane draft with a
  secret-free candidate artifact, trusted default-branch Pages controller,
  protected Preview Environment, exact-head checks, deterministic tombstone,
  and exact-branch Pages cleanup. The implementation deliberately uses
  Pydantic, official GitHub Actions, GitHub approval/Environment controls, and
  Wrangler only on their documented happy paths. Local focused and full
  contracts pass. No Git branch/commit/push/PR, organization `.github` change,
  repository setting, Environment, secret, Cloudflare resource, production,
  or destructive remote mutation has been performed.
- **Next Step**: Review the local diff and implementation evidence. Git/PR,
  cross-repository organization policy, repository settings/Environments,
  GitHub/Cloudflare credentials/resources, canary, destructive old-preview
  cleanup, and merge each retain their separate authorization gates.

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
