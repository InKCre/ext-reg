# Free-preview Option Frame

## Accepted Review Promise

The human reviewer only needs to decide whether the candidate read-only
Extension-list UI presents catalog content correctly and acceptably.

The evidence may cover:

- list structure, empty/loading/error/populated states;
- Extension Name, Nickname, version, available native distributions, and yank
  presentation when those fields are part of the accepted UI;
- responsive layout and basic browser interaction that does not mutate state;
- exact candidate revision and fixture/snapshot identity.

It explicitly does not cover an interactive Registry API, publishing,
installation, runtime loading, authentication, persistence, performance, or
availability. Those remain automated contract and black-box responsibilities.

## Candidates To Investigate

Batch 2 has ranked the candidates; the preferred option is still awaiting Sir's
review.

### Checked screenshots and job evidence

- Build the exact candidate UI against deterministic review data, exercise it in
  a browser, and attach screenshots plus machine-readable evidence to the run.
- Incremental infrastructure cost and credential exposure are zero.
- Lowest review convenience and no interactive public URL.

### Short-retention checked UI artifact

- Store the exact static UI output as a bounded-lifetime Actions artifact with a
  documented local viewer or packaged browser report.
- Preserves the candidate build without Registry infrastructure or deploy
  credentials.
- Reviewer setup and artifact-access friction must be measured.

### Static remote UI

- Serve only the exact static candidate UI and deterministic review data from a
  credential-safe trusted delivery lane.
- Provides the best human convenience without a Registry API or mutable data
  plane.
- Must prove zero incremental recurring cost, bounded retention/concurrency,
  exact-source traceability, fork behavior, and cleanup.
- **Rank**: Preferred when implemented as one fixed Pages Direct Upload project,
  not one infrastructure stack per PR.

### Checks-only fallback

- Retain full candidate checks and Worker black-box tests but publish no separate
  human Preview surface.
- Valid when the other forms are not meaningfully useful, free, or governable.

## Candidate Ranking

1. One fixed Cloudflare Pages Direct Upload project with isolated per-PR branch
   aliases and a trusted controller.
2. Short-retention checked HTML/screenshots artifact.
3. Checks-only.

Cloudflare Pages Git integration is not preferred: it avoids an API token but
uses the account-wide 500-build monthly queue, builds candidate code separately
from the admitted GitHub check, and does not itself retire the latest deployment
for a closed branch. GitHub Pages is not preferred because it offers one site per
repository but no native per-PR alias/deployment model; maintaining multiple PR
paths would add a shared aggregation state and concurrency protocol.

## Rejected For This Promise

- Per-PR Registry Worker plus D1/R2 is disproportionate and outside the accepted
  human review promise.
- A shared mutable preview Registry is rejected because it introduces
  cross-PR interference and staging authority without improving the accepted
  visual decision.
- Candidate-controlled remote deployment with any Cloudflare credential is
  rejected regardless of nominal free-tier capacity.

## Evaluation Criteria

For each candidate collect:

1. reviewer decision enabled;
2. controller and source identity;
3. credential capability and storage owner;
4. mutable resources and cross-PR interference;
5. free-tier quotas, maximum concurrent PRs, retention, and cleanup guarantees;
6. artifact/source traceability;
7. fork behavior;
8. failure and residue behavior;
9. implementation and ongoing maintenance cost;
10. what the preview does **not** prove.
