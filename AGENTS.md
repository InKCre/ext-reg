# InKCre Extension Registry

This repository owns the public Extension release contract, catalog and admission rules, developer tooling, and distribution infrastructure for InKCre. It does not own deployment installation state, peer enablement, runtime activity, or every first-party extension implementation.

## Repository Map

- `docs/`: durable repository-owned knowledge and navigation.
- `tasks/`: active, disposable task control surfaces.
- `.agents/skills/svc/`: generated local SVC integration; do not edit by hand.

## Knowledge Owners

- Shared InKCre product truth and cross-unit contracts remain in `InKCre/docs`.
- Registry-specific executable truth should prefer schemas, code, configuration, tests, assertions, and delivery automation.
- Expensive Registry-local design truth that cannot be preserved mechanically belongs under `docs/`.
- Active evidence, decisions, uncertainties, and next actions belong in the current task packet.

## Working Rules

- Default to Python for Registry tooling and services. Use TypeScript only where a browser or `client-web` contract requires it.
- Keep manifest and protocol truth language-neutral so every peer validates the same contract.
- Require explicit human authorization before modifying code or project state; task-packet maintenance is the exception.
- Require separate explicit authorization for commits, pushes, releases, remote creation, publication, production changes, and cross-repository mutation.
- Preserve the distinction between Registry releases, deployment `installed`, peer/client `enabled`, and runtime `running` state.
- Do not introduce arbitrary runtime code download into `core-py` without an approved security and lifecycle contract.

## Current Checks

- Install frozen dependencies: `uv sync --frozen && pnpm install --frozen-lockfile`.
- Run the full repository contract: `pnpm check`.
- Inspect SVC integration: `svc status --json`.
- Verify patch whitespace: `git diff --check`.
- Task-specific commands and production evidence must be recorded in the active packet.

<!-- svc:begin navigation sha256=01d8643023a40533a997a67c70e920bb0ff0056081d2d18bec59e47324318152 -->
## SVC

This project uses the local Sustainable Vibe Coding CLI. Query framework guidance when it is needed instead of copying framework documents into this repository.

- Use `svc lookup --keyword "<need>"` to find relevant guidance, then `svc lookup --name '<exact-path-regex>'` to read an authoritative document.
- Use `svc status` before broad process changes. If the installed corpus is newer than the adopted version in `svc.json`, read its migration guidance before `svc adopt`.
- Treat all unmarked project instructions and documentation as consumer-owned.
<!-- svc:end navigation -->
