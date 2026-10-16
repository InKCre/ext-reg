# InKCre Extension Registry

The public Extension release control plane, native Distribution hosting, and the independent Extension Developer Toolkit for InKCre.

## Mental Model

InKCre is a system of heterogeneous peers sharing one info-base. Extensions add capabilities to the peer they run on. Different Distributions of the same extension participate in the shared system under one business and data contract; no Distribution is the "central" implementation.

The Extension Registry is the public control plane for extension Releases and native Distributions. Registry, Toolkit, Host SDKs, and first-party Extensions are independent release units. The Toolkit must not create reverse dependencies into the Registry service.

Registry Release, deployment `installed`, Peer `enabled`, and process/browser `running` are four distinct authorities. Conflating them produces broken lifecycle behavior.

## Knowledge Owners

`ext-reg` is an SVC Spoke. Shared Hub truth is mounted read-only at `docs/_shared/` (git submodule → `InKCre/docs`).

- Product behavior and language: `docs/_shared/10-prd/`
- Cross-unit contracts and topology: `docs/_shared/20-product-tdd/`
- Registry and Toolkit internal design: `docs/30-unit-tdd/`
- Runtime, packaging, delivery, migration, and recovery: `docs/40-deployment/`
- Executable facts: source, schemas, configuration, tests, and CI
- Volatile task state: `tasks/`
- Subtree-specific hazards: the nearest local `AGENTS.md`

## Repository Map

- `src/inkcre_extension_registry/`: Registry contracts and Worker service (Python)
- `src/worker.py`: Cloudflare Worker entrypoint
- `toolkit/`: independently released developer and delivery tooling (Python, `inkcre_extension_toolkit`)
- `contracts/`: generated schemas and OpenAPI; never edit by hand
- `migrations/`: checked-in D1 schema history (append-only after deployment)
- `scripts/`: contract generation, verification, and release tooling
- `runtimes/`: runtime topology for local and preview
- `docs/30-unit-tdd/`: internal design
- `docs/40-deployment/`: runtime and delivery truth
- `tasks/`: volatile task packets

## Development Constraints

- Default to Python. Use TypeScript only at a browser or `impl-ts` seam.
- Keep manifest and protocol truth language-neutral.
- Install with `uv sync --frozen && pnpm install --frozen-lockfile`. Exact commands live in `package.json` and `pyproject.toml`.
- Never hand-edit `contracts/*`; change the source model or route and run `pnpm contracts:generate`.
- Treat checked-in D1 migrations as append-only after deployment. Production resource mutation requires a separate, explicit authorization.

## Governance And Workflow

- Git and GitHub workflow: [Git and GitHub Governance](https://github.com/InKCre/.github/blob/main/GOVERNANCE.md) and [Contributing](https://github.com/InKCre/.github/blob/main/CONTRIBUTING.md)
- Verification and test selection: [Verification and Test Policy](https://github.com/InKCre/.github/blob/main/TESTING.md)

<!-- svc:begin -->
## SVC

Use `svc --help` or `svc <command> --help`.

- `svc status`: inspect project state
- `svc dev`: manage declared development targets

If `AGENTS.local.md` exists, read it after this file. It is ignored local guidance; shared rules belong here.
<!-- svc:end -->
