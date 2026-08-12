# Independent Overdesign Review — 2026-08-12

## Verdict

**Request changes.** The prior whole-plan pass is invalidated.

An independent read-only reviewer examined this packet, the ext-reg workflows,
and `InKCre/.github` with emphasis on overdesign, tunnel vision, and missed
connections to organization governance.

## Governing Evidence

- Organization governance requires every external fork contributor to receive
  maintainer approval before even secret-free Actions start.
- That approval does not grant Preview or production credentials.
- A remote Preview is allowed only for a same-repository pull request, through a
  trusted controller that verifies exact workflow/PR/head identity and uses a
  Preview-scoped Environment.
- Live ext-reg state is weaker than the policy: the fork approval setting is
  currently `first_time_contributors`, not `all_external_contributors`.

The first three facts are owned by `../.github/GOVERNANCE.md`; the live setting
was read through GitHub's repository Actions permission API on 2026-08-12.

## Overdesign Found

1. The trusted controller was specified as a browser-content security parser,
   with an HTML element/attribute grammar, CSS URL/import/expression analysis,
   fixture-to-card semantic comparison, and content digest graph. This is not an
   organization governance requirement.
2. A changed-file classifier attempted to infer whether each PR deserved a
   Preview. It duplicates event policy, can miss indirect UI dependencies, and
   saves little at the expected volume of trusted same-repository PRs.
3. Candidate `fixture.json`, candidate `preview.json`, and two candidate-computed
   digests duplicated identity already owned by the GitHub run/artifact and the
   trusted controller.
4. Explicit per-PR GitHub Deployment creation/inactivation duplicated the audit
   record GitHub creates for an Environment job.
5. Manual deletion of one-day Actions artifacts duplicated bounded platform
   retention.

These controls increased implementation and test surface without protecting a
corresponding authority boundary.

## Boundaries That Remain Necessary

- Secret-free candidate checks, frozen dependencies, and the real local Worker
  black box remain required.
- External fork workflows require maintainer approval and never receive remote
  Preview delivery.
- A same-repository Preview still uses a protected-main `workflow_run`
  controller, exact current-head verification, a dedicated Preview Environment,
  and a Pages-only token. Maintainer approval does not replace these credential
  boundaries.
- The controller accepts only one bounded regular `index.html`, writes trusted
  `preview.json` and `_headers`, and deploys to one fixed Pages project/PR branch.
  It does not inspect HTML/CSS semantics.
- Close cleanup replaces the stable branch alias with a trusted tombstone and
  may delete older exact-branch Pages deployments. It does not manage a second
  GitHub Deployment lifecycle or manually delete expiring artifacts.
- Production credentials, exact-main delivery, and the Registry data plane stay
  separate and unchanged.

## Reviewer Findings Incorporated

- Make `all_external_contributors` an explicit rollout and acceptance item.
- Prove during the first canary that a protected-main Preview Environment is
  compatible with the `workflow_run` controller ref; failure selects the
  already-defined artifact-only fallback.
- Remove strict HTML/CSS validation rather than merely weakening its grammar.
- Remove UI-path eligibility classification and deploy every same-repository PR
  through the same fixed project.
- Keep trusted controller, exact identity, Environment/token separation,
  concurrency, tombstone cleanup, and artifact-only fallback.

## Status

This document is a historical request-changes snapshot. Its findings were
applied to the replacement HLD and implementation plan, which subsequently
passed the independent review recorded in `97-simplified-plan-review.md`. The
request-changes marker here does not describe the current packet status.
