# Active State — Runtime-family correction

- **Status:** source implementation authorized for all planned batches
- **Authority:** [D041–D043](../30-decisions-and-questions.md) plus the active
  Impact Handshake and implementation plan
- **Supersedes:** implementation authority in `79–82`
- **Evidence:** current inventories in `78`, `80` and Core/Client feature
  worktrees; historical files remain read-only evidence

## Authorized Now

- source implementation for all local batches;
- investigation and bounded experiments;
- task-packet maintenance;
- plan and readiness review.

## Not Authorized Yet

- commits or pushes;
- package publication;
- further cross-repository mutation outside the authorized Core/Client adoption worktrees;
- preview or production deployment;
- PR merge.

## Current Gate

Batches 1–3 and local package-release preparation are complete. Toolkit 0.2.0
and both Runtime 0.1.0 packages must be committed, pushed and published before
the Peer manifests can receive normal released dependencies and frozen locks.
Every remote mutation remains separately gated.
