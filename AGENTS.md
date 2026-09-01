# InKCre Extension Registry

This repository owns the public Extension release control plane, native
Distribution hosting, and the independent Extension Developer Toolkit.

## Repository Map

- `src/inkcre_extension_registry/`: Registry contracts and Worker service.
- `toolkit/`: independently released developer and delivery tooling.
- `contracts/`: generated schemas and OpenAPI; never edit by hand.
- `migrations/`: checked-in D1 schema history.
- `docs/`: durable local knowledge; `tasks/`: volatile task packets.

## Knowledge Owners

- Shared InKCre product truth and cross-unit contracts: `InKCre/docs` Hub.
- Registry and Toolkit internal design: `docs/30-unit-tdd/`.
- Runtime, packaging, delivery, migration, and recovery: `docs/40-deployment/`.
- Executable facts: source, schemas, configuration, builds, and automation.
- Active evidence and provisional decisions: current `tasks/*/packet.md`.

## Working Rules

- Never edit `docs/_shared/**` from this Spoke. Use
  `.agents/skills/edit-svc-shared-docs/` to change the Hub source first and bump
  the local shared reference separately.
- Default to Python. Use TypeScript only at a browser or `client-web` seam.
- Keep manifest and protocol truth language-neutral.
- Preserve Registry Release, deployment `installed`, Peer `enabled`, and
  process/browser `running` as distinct authorities.
- Registry, Toolkit, Host SDKs, and first-party Extensions are independent
  release units. Do not create reverse dependencies from the Toolkit into the
  Registry service.
- Never hand-edit `contracts/*`; change its source model or route and run
  `pnpm contracts:generate`.
- Treat checked-in D1 migrations as append-only after deployment. Production
  resource mutation requires a separate, explicit authorization.

## Current Checks

- Follow the organization-wide
  [Verification and Test Policy](https://github.com/InKCre/.github/blob/main/TESTING.md); the checks below are Registry-local
  verification contracts, not a separate testing policy.
- Install frozen dependencies: `pdm install --frozen-lockfile && pnpm install --frozen-lockfile`.
- Run the full repository contract: `pnpm check`.
- Generate contracts intentionally: `pnpm contracts:generate`.
- Inspect SVC integration: `svc status --json`.
- Verify patch whitespace: `git diff --check`.
- Task-specific commands and production evidence must be recorded in the active packet.
- Read the active packet before changing its governed scope. Keep production
  evidence and task-specific verification there.

<!-- svc:begin -->
## SVC

Use `svc --help` or `svc <command> --help`.

- `svc status`: inspect project state
- `svc lookup`: read SVC guidance
- `svc task init`: create a task packet
- `svc task grow`: inspect packet shape without changing files
- `svc dev`: manage declared development targets

If `AGENTS.local.md` exists, read it after this file. It is ignored local guidance; shared rules belong here.
<!-- svc:end -->
