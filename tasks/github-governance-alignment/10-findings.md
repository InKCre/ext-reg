# Governance Findings

## Compliance Matrix

| Surface | Observation | Disposition |
| --- | --- | --- |
| Formal scope | `ext-reg` is absent from the organization enforcement list and repository profiles. | Governance gap; add explicitly or record a bounded exception. |
| Protected `main` | PR, strict current-base check, App binding, conversations, admin enforcement, linear history, no force/delete are active. | Conforms. |
| Approvals | Required approving review count is zero. | Conforms to the initial baseline. |
| Merge methods | Squash/rebase and merge commits are enabled. | Disable merge commits; keep squash default and rebase intentional. |
| Branch cleanup | Automatic branch deletion is disabled. | Conforms; manual cleanup remains intentional. |
| Default Actions token | Repository default is write and Actions may approve PRs. | Set default read-only and disable PR approval. |
| External contributor approval | Live policy is `first_time_contributors`; organization governance requires every external fork contributor to be approved before Actions run. | Set and verify `all_external_contributors`; approval remains secret-free CI only. |
| Action pinning | Every checked-in third-party Action uses an immutable commit SHA. | Conforms in source; live SHA-pinning enforcement is absent. |
| Required context naming | Required context is `Native Registry and Worker contract`. | Adopt `ext-reg checks` during this substantive workflow change and update protection atomically. |
| Candidate validation | Frozen dependencies, full checks, real local Worker smoke, exact head, and fork gating exist. | Strong evidence lane, but must stay secret-free. |
| Preview controller | Candidate workflow code receives the deploy credential. | Critical authority violation; move delivery to a trusted controller. |
| Preview credential | Preview and production consume the same account token. | Critical authority violation; candidate code must never receive production capability. |
| Preview state | Every PR migrates and seeds one persistent shared D1. | Violates isolated/short-lived resources and the ban on PR mutation of shared staging. |
| Preview Environment | Main creates dynamic per-PR Environments; the local cleanup draft creates none. | Neither is the desired shape; use a durable protected `preview` Environment if remote delivery remains. |
| Preview cleanup | Main leaves aliases/Environments; local draft has deterministic Worker cleanup and concurrency. | Preserve cleanup semantics after authority redesign. |
| Production source | Manual delivery accepts an exact SHA, proves it is current `main`, runs full checks, migrates, deploys, and smokes. | Largely conforms. |
| Production Environment | Environment has no main-only policy/protection and owns no deploy secret. | Live state contradicts the documented credential boundary. |
| Production evidence | Source and run are visible, but the summary still claims deleted rollback resources remain and does not preserve an explicit Worker Version identity. | Correct stale evidence and strengthen deployment identity. |
| PR descriptions | Recent PRs omit some risk, rollback, delivery, and stack fields. | Use the inherited organization template completely. |

## Causal Diagnosis

The preview design optimized first for functional availability and later for
residue cleanup. It did not first define the credential authority or the minimum
preview promise. Consequently one account token became a convenient shared
deployment mechanism, a persistent D1 became a shared fixture, and dynamic
Environments became presentation state. Per-PR Workers fix naming and teardown
but do not repair that causal boundary.

The governance repair should therefore begin with the human decision the preview
supports and the authority it truly needs, not with another Cloudflare resource
layout.
