# Context And Live Evidence

## Authorities

- Organization policy:
  [`InKCre/.github` Governance](https://github.com/InKCre/.github/blob/main/GOVERNANCE.md)
  and
  [`CONTRIBUTING.md`](https://github.com/InKCre/.github/blob/main/CONTRIBUTING.md).
- Repository workflow implementation:
  [Registry checks](../../.github/workflows/ci.yml) and
  [production delivery](../../.github/workflows/production.yml).
- Repository operations contract: [Operations](../../docs/operations.md).
- Live GitHub repository settings and Cloudflare resources are operational
  state, not truth owned by this packet.

## Evidence Snapshot — 2026-08-11

### Governance scope

The organization enforcement list names `core-py`, `client-web`, `ui`, and
`docs`; it does not name `ext-reg` or define its repository profile. The
organization contribution guide nevertheless describes its workflow as
organization-wide and forbids repository-local weakening.

### Protected main and merge policy

- `main` requires pull requests, strict latest-base status checks, resolved
  conversations, administrator enforcement, linear history, and a GitHub
  Actions App-bound required context.
- Force push and branch deletion are disabled; zero approvals is the accepted
  baseline.
- Squash and rebase are enabled, and recent PRs entered `main` as one-parent
  squash commits.
- Merge commits are still enabled. Automatic branch deletion is disabled.

### Actions and Environments

- Repository default workflow-token permission is `write`.
- Actions are allowed to approve pull-request reviews.
- Public-fork workflow approval is `first_time_contributors`; organization
  governance requires every external contributor to receive maintainer approval
  before secret-free Actions start, so the target is
  `all_external_contributors`.
- Checked-in third-party Actions are pinned to immutable commit SHAs.
- The `production` Environment exists but has no deployment branch policy,
  protection rule, or Environment-owned secret.
- `CLOUDFLARE_API_TOKEN` is an organization Actions secret selected for this
  repository and is consumed by both preview and production jobs.

### Preview authority

The current protected-main workflow runs on `pull_request`, checks out the exact
candidate head, applies migrations and a fixture to one persistent preview D1,
and deploys with the same Cloudflare token used for production. Same-repository
and fork checks, deterministic naming, exact-head checkout, smoke checks, and
concurrency exist, but the controller and credential are not isolated from
candidate code or production authority.

The pending local `hotfix/preview-cleanup` changes one shared preview Worker plus
aliases into a namespaced Worker per PR and adds trusted close cleanup. It also
removes the dynamic GitHub Environment to avoid administrative cleanup residue.
That draft is uncommitted and unpushed; it solves residue, not governance.

### Pull-request evidence

Recent PRs carry intent and check evidence, but do not consistently preserve the
organization template's explicit risk, rollback, delivery/credential effects,
and stack relationships.

## Material Constraints

- GitHub Free limits which organization-wide enforcement features are
  available; repository settings remain the enforcement unit.
- Cloudflare free-tier quotas and resource-count/lifecycle limits have not yet
  been measured for a per-PR Worker plus data plane.
- A useful preview is optional under organization governance. PR checks remain
  mandatory; an unsafe or uneconomic preview is not.
- Production is a public demo, but that does not make production authority an
  acceptable PR credential.

## Accepted Preview Boundary — 2026-08-11

- Human Preview evidence is limited to the read-only Extension-list UI.
- It may use deterministic candidate-bound review data and does not need a live
  Registry API or mutable preview data plane.
- Interactive Registry behavior, native distribution publication and reads,
  installation, and runtime integration remain automated black-box evidence.
- Historical investigation began with the delivery form undecided. Batch 2 has
  since selected one fixed Pages Direct Upload project, with artifact-only as
  the explicit fallback; the HLD and implementation plan own current truth.
