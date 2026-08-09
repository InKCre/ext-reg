# InKCre Extension Registry

The public package registry and Runtime/API contracts for InKCre Extensions.

The Registry stores immutable, multi-target Extension Versions. Producers publish target artifacts
from their own repositories; a deployment selects compatible targets, installs one exact Extension
Version, and keeps peer enablement separate from installation.

The MVP service runs as a Python Cloudflare Worker with D1 metadata and content-addressed R2
artifacts. `@inkcre/extension-runtime` provides the browser lifecycle, compatibility matcher, and
Registry client contract.

## Local checks

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
pnpm install --frozen-lockfile
pnpm check
```

The active delivery plan and evidence live in
[`tasks/extension-registry-mvp/packet.md`](tasks/extension-registry-mvp/packet.md).
