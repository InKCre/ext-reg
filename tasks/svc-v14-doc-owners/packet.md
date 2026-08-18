# SVC v14 and Durable Knowledge Owners

- **Outcome**: Adopt SVC 14.0.0 and reduce repository documentation to one
  durable owner per stable fact, with admitted Unit TDD and Deployment
  surfaces instead of mixed root-level architecture and operations files.
- **Guardrails**: Preserve executable authorities and the Registry / Toolkit /
  deployment / Peer-runtime boundaries. Do not modify source, contracts,
  workflows, migrations, or the active `extension-setup-wizard` packet. Treat
  its existing dirty files as user-owned and exclude them from this task's
  commit surface.
- **Verification**: SVC reports schema 3, Corpus 14.0.0, current generated
  guidance, and no pending upgrade. Retained Markdown links resolve;
  `git diff --check` and `pnpm check` pass. The final diff separately proves
  that user-owned task edits were not changed by this task.
- **Current truth**: The project now uses schema 3 and Corpus 14.0.0. SVC
  status is healthy; `init` and `upgrade` are noops. Registry and Toolkit
  internals now live in Unit TDD, operational truth is split by runtime and
  delivery consumer, and mixed root-level owners are removed. Completed MVP
  and governance packets have been deleted; the active setup-wizard packet and
  its user-owned dirty files are untouched by this task.
- **Decisions**: Use `docs/30-unit-tdd/` for expensive Registry and Toolkit
  internals, `docs/40-deployment/` for runtime and delivery truth, root
  `AGENTS.md` for repository routing/workflow, and executable surfaces wherever
  they can prevent drift. Delete completed packets without archiving them.
- **Verification result**: Durable/root Markdown formatting and relative links
  pass, `git diff --check` passes, and `pnpm check` passes with 44 tests, zero
  Pyright diagnostics, both package builds, and the Worker dry build. The host
  currently runs Node 26 rather than the declared Node 22, producing an engine
  warning without a check failure.
- **Next step**: Create the authorized single task-scoped commit. Push, PR,
  merge, and deletion of this packet remain outside the current authorization.
