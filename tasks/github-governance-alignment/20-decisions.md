# Decisions

## D001 — Organization governance is the target baseline

- **Status**: Accepted.
- `ext-reg` must not rely on omission from the current enforcement list as
  permission to weaken organization workflow rules.
- Formal scope/profile adoption is part of this follow-up and is a separate
  cross-repository mutation.

## D002 — The current cleanup workflow is not mergeable as-is

- **Status**: Accepted.
- Namespaced Worker cleanup is useful evidence, but removing the preview
  Environment and retaining the shared production-capable credential/data path
  does not satisfy governance.
- The local branch remains historical evidence, not an implementation candidate
  or approved state diff. Only independently applicable cleanup/concurrency
  techniques may be reused if the selected UI-evidence topology needs them.

## D003 — Zero incremental recurring preview cost is a hard constraint

- **Status**: Accepted.
- Do not assume a Worker, database, object store, Environment, or deployment per
  PR is feasible merely because the API can create it.
- Cost includes quota exhaustion, retained-resource limits, cleanup operations,
  and maintenance burden, not only an invoice line item.

## D004 — Remote preview is optional

- **Status**: Accepted.
- Required candidate checks cannot be weakened for preview convenience.
- If no useful, isolated, credential-safe, free solution exists, checks-only is
  preferable to a nominal preview.

## D005 — Preview selection follows its review promise

- **Status**: Accepted.
- Human Preview evidence exists only to review the read-only Extension-list
  UI's layout, content presentation, and candidate visual behavior.
- It does not promise an interactive Registry API, publisher upload, Simple API,
  Module Federation delivery, installation, enablement, runtime behavior,
  persistence, authentication, performance, or availability.
- Registry API and native distribution behavior remain mandatory automated
  black-box evidence against candidate code.
- The delivery form remains open: static remote output, short-retention review
  artifact, screenshots plus checked output, or checks-only if no useful free
  remote form satisfies governance.

## D006 — Live settings and cross-repository changes require impact handshakes

- **Status**: Accepted.
- Organization policy, repository protection, Actions permission, Environment,
  secret, Cloudflare, required-context, workflow, and PR changes must be
  presented as bounded state diffs before mutation.

## D007 — UI Preview data is deterministic review input, not shared staging

- **Status**: Accepted.
- UI Preview may consume a deterministic fixture or generated catalog snapshot
  whose provenance is tied to the candidate revision.
- It must not migrate, seed, or mutate a shared preview D1/R2 data plane.
- Contract drift between fixture and service must be caught by executable
  schema/contract checks; a visually correct fixture is not API evidence.

## D008 — Do not select infrastructure before evidence

- **Status**: Accepted.
- No Worker, Pages project, deployment Environment, database, bucket, token, or
  organization/repository setting will be created or changed during option
  investigation.
- Current quotas and product behavior must be verified from primary sources and
  bounded non-persistent experiments before an HLD chooses a delivery form.

## D009 — Prefer one fixed Pages Direct Upload project

- **Status**: Accepted.
- Use one preview-only Cloudflare Pages project with deterministic per-PR branch
  aliases; do not create a Worker, D1 database, R2 bucket, Pages project, or
  custom domain per PR.
- Candidate CI is secret-free and produces one bounded static `index.html`.
  A trusted `workflow_run` controller from
  protected `main` verifies the exact successful same-repository PR head, treats
  the artifact as static review data, adds trusted source identity and headers,
  and uploads it through the protected `preview` Environment.
- Use a dedicated Pages-only credential, never the Registry production token.
  Cloudflare exposes Pages Write at account scope rather than individual-project
  scope; this residual authority must be explicit in the HLD and impact
  handshake.
- Closing a PR replaces its stable alias with a trusted tombstone. Older
  immutable deployments may be deleted; Cloudflare does not allow deletion of
  the latest deployment for a branch, so one policy-owned tombstone remains.
- Fork PRs receive checks and artifacts only, never remote delivery.

## D010 — Keep an artifact-only fallback

- **Status**: Accepted.
- If Pages quota, authority, or retention evidence fails during HLD/acceptance,
  retain the exact static UI as a short-retention GitHub Actions artifact and do
  not create another remote preview topology.
- Checks-only remains the final fallback if even artifact review has no useful
  human value.

## D011 — A complete implementation plan precedes every start request

- **Status**: Accepted protocol invariant.
- "Start" may be requested only after the selected design has an implementation-
  ready plan covering exact files and deletions, interfaces and data shapes,
  workflow events and authority, external state diffs, sequencing, failure and
  cleanup behavior, rollback, verification commands, and black-box acceptance.
- Product selection, option research, an HLD, or a roadmap alone is not an
  implementation plan.
- The plan must receive a fresh whole-plan review with no unresolved blocker,
  contradictory status, placeholder, or deferred design decision before it is
  presented to Sir.
- A start authorization obtained after an incomplete or inaccurately reported
  plan is invalid and must not be reused.

## D012 — Remote delivery is limited to UI-affecting pull requests

- **Status**: Superseded by D013.
- The file classifier was an unnecessary custom policy mechanism. It could miss
  indirect UI inputs, duplicated GitHub's event/identity controls, and added
  more code than the expected volume of trusted same-repository pull requests
  justifies.

## D013 — GitHub's contributor approval is the untrusted-code gate

- **Status**: Accepted after independent overdesign review.
- Set the public-fork approval policy to `all_external_contributors`, matching
  organization governance. The current `first_time_contributors` setting is
  drift, not an accepted weaker policy.
- Approval permits only secret-free candidate checks. Fork pull requests never
  receive the Preview Environment and never cause remote Pages delivery.
- Remote Preview remains limited to same-repository pull requests. A trusted
  default-branch `workflow_run` controller verifies the successful run, pull
  request, repository, and exact current head before using the Preview
  Environment.
- Every same-repository pull request may receive the tiny static Preview. This
  removes a brittle changed-file classifier and keeps the topology legible.

## D014 — Do not build a browser-content security parser

- **Status**: Accepted after Sir's correction and independent review.
- The candidate artifact is one bounded regular `index.html`. The trusted
  controller copies only that file and generates `preview.json` plus `_headers`
  itself.
- The controller verifies artifact/run/head identity, file type, name, and size;
  it does not parse, sanitize, or allowlist candidate HTML or CSS.
- Browser policy remains a platform concern: controller-owned headers apply
  noindex, no-store, nosniff, no-referrer, and a restrictive CSP. A future UI
  that needs scripts or assets must explicitly revise that header contract.
- This consciously accepts that an authorized same-repository contributor can
  change the visual document served on an isolated Preview origin. Such a
  contributor can already propose the same source change; production remains
  protected by review, required checks, and protected-main delivery.

## D015 — Prefer mature-tool happy paths over custom control frameworks

- **Status**: Accepted implementation constraint.
- Minimal dependency count is not the objective. Prefer a mature framework or
  library when its documented happy path already owns a generic concern and the
  repository can pin and test that integration.
- Use existing Pydantic/FastAPI contracts for product data, official GitHub
  Actions for checkout/artifact transfer, GitHub's native contributor approval
  and Environments for trust, and Wrangler for Pages deployment/retirement.
- Custom code owns only InKCre-specific rendering, identity decisions, and
  orchestration gaps that those tools do not express.
- Do not stretch a framework beyond its promised path merely to avoid a small
  explicit adapter. Conversely, do not add a general-purpose dependency for a
  narrow operation already safely covered by the standard library.
