# Superseded Whole-plan Review — 2026-08-12

## Result

**Superseded.** This review previously passed the HLD and implementation plan,
but Sir's follow-up and an independent review found that it treated candidate
HTML/CSS as an adversarial language requiring a custom parser even though the
organization's contributor-approval and same-repository Preview controls own
that trust decision. It also retained a brittle path classifier and duplicate
GitHub Deployment/artifact retirement bookkeeping.

The pass below is historical evidence only and no longer makes the plan
implementation-ready. It does not authorize
repository code, workflow, GitHub, Cloudflare, credential, destructive,
cross-repository, Git, PR, or merge mutations.

The corrections made during review were:

1. remote Pages delivery is limited to trusted-controller-classified
   UI-affecting PRs instead of spending quota on backend-only changes;
2. Preview delivery and close cleanup share one exact per-PR concurrency group;
3. trusted HTML validation now covers CSS/network references and exact
   fixture-to-card/href correspondence, not only tag names;
4. production delivery gains a read-only credential-verification mode so the
   Environment-owned token can be proven before shared-token access is removed;
5. the plan distinguishes explicit candidate GitHub Deployments from the fixed
   Preview Environment's automatic trusted-controller audit records.

## Gate 0 — Implementation-plan Completeness

Pass.

- Exact files to add, edit, replace, and retain are named for both repositories.
- Static fixture, artifact, identity, deployed-file, header, and tombstone
  shapes are fixed.
- Workflow triggers, names, contexts, permissions, Environment use, token names,
  concurrency, fork behavior, bootstrap behavior, and failure paths are fixed.
- GitHub/Cloudflare before-and-after state, required-context migration, token
  separation, legacy resource cleanup, and irreversible boundaries are fixed.
- Focused, full, workflow, live canary, cleanup, production-regression, quota,
  and residue evidence are named with commands or exact observations.
- No placeholder, schema choice, naming choice, topology option, or semantic
  implementation decision remains deferred.

## Product And Topology Review

Pass.

- Human evidence truthfully covers only the read-only Extension-list UI.
- Every Registry protocol and native distribution promise remains in the local
  real-Worker black box.
- One fixed static Pages project replaces the rejected per-PR Registry service;
  no D1/R2/Worker/Functions/custom-domain state is introduced per PR.
- Backend-only PRs receive automated checks and artifact evidence but no
  meaningless remote UI URL.
- Preview links point to production API reads and cannot imply that candidate
  Registry APIs are running behind the static origin.

## Authority And Adversarial Review

Pass.

- Candidate code receives only read access and cannot obtain Preview or
  production credentials.
- The merge candidate and exact-head artifact are separate identities and both
  are checked before delivery.
- `workflow_run` verifies name, path, success, repository, one open PR, current
  head, changed-file eligibility, and exact artifact before Environment access.
- The trusted controller checks out protected-default-branch code and treats
  candidate files only as bounded data. It cannot execute `_worker.js`, a
  Functions tree, package archive, symlink, script, handler, external resource,
  or candidate header policy.
- Preview and production tokens are separated by Environment and Cloudflare
  permission. Pages Write remains account-scoped only because Cloudflare has no
  project-scoped equivalent; the residual is explicit and the trusted command
  pins project/branch.
- `pull_request_target` exists only in close cleanup, validates a closed internal
  PR, and never checks out candidate code.

## Event, Race, And Failure Review

Pass.

- Cancelled/failed upstream workflows cannot trigger delivery.
- A moved head, closed PR, fork, ambiguous associated PR, missing artifact,
  changed workflow identity, invalid artifact, or missing Environment fails
  closed.
- Delivery and cleanup use the same concurrency key, so a tombstone cannot be
  overwritten by an older candidate run. Identity is rechecked immediately
  before mutation.
- An update cancels stale delivery; a close queues non-cancellable cleanup.
- The first introducing PR correctly has no Pages Preview because a
  `workflow_run` workflow must already exist on default branch. The canary after
  merge is the first valid remote proof.
- Pages failure cannot fall through to production, a new project, or another
  remote topology. Artifact-only review is the bounded fallback.

## Governance And Migration Review

Pass.

- Organization scope is changed in its owner repository and merged before live
  ext-reg enforcement.
- The migration PR first produces the new App-bound check; branch protection
  then replaces the old context in one full payload. Main never has an empty or
  unbound required check.
- Merge commits and write-default Actions permissions are removed without
  changing squash/rebase, review count, conversation resolution, admin
  enforcement, strict checks, linear history, force-push, or deletion policy.
- Preview and production Environments are fixed, protected-main credential
  boundaries rather than candidate-created Environments.
- The production token is verified read-only before ext-reg loses access to the
  broader organization token.
- Obsolete fixture-only preview D1/R2 deletion is last, exact-targeted,
  separately authorized, and occurs only after the Pages fallback is proven.

## Cost And Retention Review

Pass with one measured acceptance condition.

- Persistent incremental state is one Pages project (project 7 of the current
  Free allowance of 100) and one latest tombstone for each UI-affecting closed
  PR branch.
- Candidate artifacts are tiny and retained one day; older branch deployments
  and artifacts are retired.
- Direct Upload uses prebuilt output and no Git provider. Cloudflare documents
  its 500 monthly build limit in the Git-repository build section, but does not
  make an equally explicit quota statement for every Direct Upload deployment.
  The canary therefore must record project source/provider and account build
  observations. Any unexpected charge/build-quota consumption activates the
  artifact-only fallback.
- This is a verification condition, not an unresolved design choice: the
  fallback and switch criterion are already fixed.

## Production And Rollback Review

Pass.

- `registry.inkcre.dev`, native-v2 D1/R2 bindings, publication behavior, and
  exact-main source authority are unchanged.
- Production `verify` is read-only; `deploy` alone can migrate/deploy.
- Preview rollback is removal/disablement of the controller plus artifact-only
  evidence and never touches production.
- Required-context rollback restores a passing old job before restoring its
  App-bound context.
- After the old preview D1/R2 pair is explicitly deleted, its fixture data is
  intentionally non-recoverable; this is unrelated to production rollback.

## Verification Review

Pass.

- Unit tests cover rendering, origin validation, deterministic identity,
  artifact bounds, hostile paths/types/HTML/CSS, cleanup selection, and workflow
  invariants.
- `actionlint`, frozen dependency installs, `pnpm check`, SVC status, and diff
  checks cover repository truth.
- The canary covers real GitHub workflow identity, Environment authority, Pages
  immutable/alias URLs, update race, closure, tombstone, deletion, and quota.
- Final audits cover repository settings, Environment/secret metadata,
  App-bound required context, Pages configuration/deployments, Actions
  artifacts, GitHub Deployments, obsolete preview variables/resources, local
  temporary files, and production anonymous reads.

## Start Eligibility

This start-eligibility result is withdrawn. The simplified replacement plan must
receive a fresh independent whole-plan review before it can be presented as
implementation-ready. Earlier start messages remain invalid for this plan.
