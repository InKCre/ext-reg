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

Batches 1–3 and the Python dependency-acquisition correction are locally
complete. Core Runtime 0.1.1 must be committed, pushed and published before
Core PR #65 can receive the released dependency and frozen lock. Its preview
producer finalization correction is locally ready in the Core worktree. Every
remote mutation remains separately gated.
