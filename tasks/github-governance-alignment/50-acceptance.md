# Acceptance Gates

## Gate 0 — Plan Completeness Before Start

- The chosen design has an implementation-ready, file-level plan rather than
  only research, a recommendation, an HLD, or a roadmap.
- The plan closes artifact shape, interfaces, workflow authority, external
  state changes, order of operations, failure/cleanup, rollback, and exact
  verification evidence.
- A fresh whole-plan review passes with no unresolved implementation decision,
  contradiction, placeholder, or stale status.
- Sir is not asked to say "start" before all three conditions hold.

## Gate 1 — Governance Ownership

- `ext-reg` appears in the organization enforcement scope and has a repository
  profile, or a bounded exception records owner, reason, controls, and review
  date.
- Repository-local guidance extends rather than weakens organization policy.

## Gate 2 — Git And Main Protection

- All main changes require a PR, latest-base repository check, resolved
  conversations, App-bound context, admin enforcement, linear history, no force
  push, and no deletion.
- Merge commits are disabled; squash is default; intentional rebase remains.
- Required-context renaming and branch-protection updates are atomic.

## Gate 3 — Actions Baseline

- Default workflow token is read-only and Actions cannot approve PRs.
- Write-capable jobs declare the minimum explicit permission.
- Every third-party Action reference is an immutable commit SHA.
- Every external fork contributor requires maintainer approval before any
  secret-free workflow starts; the live policy is
  `all_external_contributors`, not `first_time_contributors`.
- Fork jobs remain secret-free and cannot reach Preview or production
  Environments.

## Gate 4 — Candidate Validation

- Candidate code runs frozen checks and real local Worker tests without remote
  deploy credentials.
- The required check proves the exact candidate against the latest base and
  current admitted dependencies.
- PR evidence includes intent, verification, risk, rollback, delivery effects,
  and stack relationships.

## Gate 5 — Preview Or Explicit No-preview

- The selected model enables only human review of the read-only Extension-list
  UI and explicitly disclaims interactive Registry behavior.
- Candidate UI evidence identifies the exact source revision and deterministic
  fixture or generated snapshot used.
- Automated black-box checks independently cover service boot, public Registry
  reads, Python and Module Federation distribution behavior, and publication
  lifecycle where required by the repository contract.
- It has measured zero incremental recurring cost under expected concurrency,
  retention, and quota use.
- Candidate code receives no production-capable credential and cannot mutate
  shared staging or production state.
- Remote delivery, if retained, uses a trusted controller and protected preview
  Environment; names, state, concurrency, and cleanup satisfy the accepted
  topology.
- A Pages-based model uses one fixed preview-only project, no Functions or data
  bindings, no custom domain, one bounded regular `index.html`, trusted
  controller-generated source identity and headers, and a dedicated Pages-only
  credential. The account-wide residual capability of Pages Write is recorded.
- The controller does not implement a custom HTML/CSS sanitizer. It deploys only
  the bounded document and adds restrictive CSP/noindex/no-store headers from
  protected-main code.
- Closing a Pages preview replaces the stable branch alias with a trusted
  tombstone and deletes older deployments when allowed; the retained latest
  tombstone is an explicit policy-owned record rather than live candidate UI.
- Every same-repository PR may receive a Preview; forks receive neither Preview
  nor production authority even after their secret-free workflow is approved.
- No-preview is accepted when other candidates fail these conditions.

## Gate 6 — Production Authority

- The `production` Environment is restricted to `main` and owns the production
  credential boundary.
- Delivery selects exact current-main source, runs the repository contract,
  applies checked migrations, deploys, smokes, and records source/run/Worker
  Version/resource identity.
- Production summaries and rollback claims match live resource reality.

## Gate 7 — Residue And Regression

- Closing or superseding a preview leaves no Worker, live candidate alias,
  resource, secret, or temporary local residue beyond the latest trusted
  tombstone, fixed Environment audit records, ordinary one-day Actions artifact
  expiry, and provider-retained immutable deployment records explicitly allowed
  by policy.
- `registry.inkcre.dev` and native Registry publication/read behavior remain
  unchanged by governance remediation.
- A final live-settings audit and repository check both pass.
