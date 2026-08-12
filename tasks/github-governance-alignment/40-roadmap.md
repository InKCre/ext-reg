# Review And Execution Batches

## Batch 0 — Follow-up Control Surface

- **Status**: Complete.
- Preserve audit evidence, accepted constraints, open questions, and the current
  uncommitted workflow draft without treating it as an approved fix or future
  implementation base.

## Batch 1 — Preview Product Promise

- **Status**: Complete.
- Human Preview evidence covers only the read-only Extension-list UI.
- Protocol, service boot, publication, installation, and runtime journeys remain
  independent automated black-box evidence.
- Exit gate: the bounded promise and explicit non-promises are accepted.

## Batch 2 — Evidence-form And Free-tier Investigation

- **Status**: Complete; fixed Pages Direct Upload selected and accepted.
- Verify current GitHub and Cloudflare free quotas with primary sources and
  bounded experiments where necessary.
- Compare checked screenshots, short-retention artifacts, static remote UI, and
  checks-only against the accepted visual-review promise.
- Do not create persistent resources, credentials, Environments, or settings
  changes during investigation.
- Exit gate: objective cost, quota, authority, concurrency, and cleanup evidence.

## Batch 3 — Governance And Repository HLD

- **Status**: Complete; recorded in `80-governance-preview-hld.md`.
- Select the minimum Preview evidence form, then review one coherent topology in
  three adjacent state-diff groups:
  1. organization scope, repository settings, required contexts, and merge
     policy;
  2. candidate checks plus UI-review evidence, including a trusted controller
     and Environment only if remote delivery is selected;
  3. production Environment, credential boundary, exact-main delivery, and
     evidence retention.
- Exit gate: exact settings/workflow state diff and failure behavior reviewed.

## Batch 4 — Implementation-ready Plan And Whole-plan Review

- **Status**: Complete after replacement review. The prior pass in
  `95-whole-plan-review.md` was superseded by the independent request-changes
  review in `96-overdesign-review.md`; the simplified HLD and implementation
  plan then passed the fresh review in `97-simplified-plan-review.md`.
- Resolve the HLD into an exact execution specification containing:
  1. every repository file to add, change, or retire and the responsibility of
     each change;
  2. static artifact schema, rendering inputs, trusted validation, deployment
     identity, Pages alias, tombstone, cleanup, and retained-record behavior;
  3. every workflow trigger, permission, Environment, credential, concurrency,
     fork, cancellation, failure, and retry path;
  4. exact GitHub, Cloudflare, and organization-policy before/after state;
  5. rollout order, atomic required-context migration, rollback points, and
     residue cleanup;
  6. focused, full-contract, live black-box, quota, and post-change audit
     commands with expected evidence.
- Review the complete plan against the product promise, governance, free-tier
  bound, current repository state, and production non-regression requirements.
- Exit gate: a fresh review says **Pass**, every planned file/state owner and
  verification reference is explicit, and no implementation decision remains
  open.

## Batch 5 — Start Gate And Impact Handshakes

- **Status**: Partial. Sir explicitly authorized the ext-reg-local
  workflow/test/documentation implementation after the simplified plan passed.
  Cross-repository organization policy, repository settings, Environments,
  credentials/resources, Git/PR, canary, destruction, and merge remain pending
  handshakes.
- Only after Batch 4 passes may Sir be asked to say "start" for implementation.
- The earlier premature start request is void.
- Present separate handshakes for:
  1. `InKCre/.github` policy/profile;
  2. ext-reg GitHub repository settings and Environments;
  3. ext-reg workflows/tests/docs;
  4. GitHub/Cloudflare credentials or resources, if any.
- Exit gate: explicit authorization for each mutation owner.

## Batch 6 — Implementation And Migration

- **Status**: Ext-reg-local implementation complete and locally verified;
  external settings migration, organization `.github`, Git/PR delivery, and
  live canary remain pending.
- Apply settings and workflow changes in an order that never removes the only
  required check or grants a temporary bypass.
- Replace or retire the current preview lane; do not layer another lane beside
  it.
- Exit gate: local checks and repository settings audit agree.

## Batch 7 — Black-box Acceptance

- **Status**: Pending.
- Prove candidate validation, required-context freshness, preview/no-preview
  evidence, cleanup, fork behavior, production exact-main delivery, and absence
  of residual authority/state.
- Exit gate: acceptance gates pass and the follow-up packet records remaining
  non-goals.

## Sequencing Rule

- Batches are review boundaries, not authorization shortcuts.
- Finish and review one batch before entering the next.
- Closely related findings inside a batch should be investigated and presented
  together; do not ask for a series of low-value micro-decisions.
- Task-packet maintenance may proceed continuously. Code, workflow, settings,
  credential, remote, and cross-repository mutations retain their separate
  authorization gates.
- Never ask Sir to say "start" on the strength of research, recommendation,
  roadmap, or HLD alone. The Batch 4 implementation plan and fresh review are
  mandatory preconditions.
