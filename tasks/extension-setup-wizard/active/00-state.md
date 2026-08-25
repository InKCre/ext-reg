# Active State — Runtime-family correction

- **Status:** implementation and preview acceptance complete; merge authorized
- **Authority:** [D041–D043](../30-decisions-and-questions.md) plus the active
  Impact Handshake and implementation plan
- **Supersedes:** implementation authority in `79–82`
- **Evidence:** current inventories in `78`, `80` and Core/Client feature
  worktrees; historical files remain read-only evidence

## Completed Authority

- source implementation, cross-repository adoption and preview delivery;
- commits, pushes and independent package publication;
- final task-packet maintenance and merge review.

## Remaining Boundary

- Core PR #65 and Client PR #71 are authorized for squash merge after the final
  review recorded in the acceptance result.
- Production Registry publication remains owned by the normal release workflow;
  this task does not perform a manual production mutation.

## Current Gate

Runtime-family PR #18 is merged. Toolkit 0.2.1, Core Runtime 0.1.1 and Web
Runtime 0.1.0 are published; Peer locks consume them. Core #65 and Client #71
are green with successful previews. The current gate is their ordered squash
merge: Core first, then Client.
