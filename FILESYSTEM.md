# Filesystem

```text
.
├── contracts/                  generated JSON Schema, OpenAPI, revision
├── docs/                       durable navigation and operations
├── migrations/                 append-only D1 migrations
├── packages/runtime-web/       @inkcre/extension-runtime
├── scripts/                    contract generator and Worker smoke client
├── src/
│   ├── worker.py               Cloudflare top-level entry shim
│   └── inkcre_extension_registry/
│       ├── contracts/          canonical Python models/matcher/lifecycle
│       ├── service/            FastAPI plus D1/R2 adapter
│       ├── cli.py              target build/publish CLI
│       ├── client.py           typed Registry HTTP client
│       └── worker.py           Worker routing/ASGI bridge
├── tasks/                      active disposable delivery control surface
├── tests/                      focused contracts, service, and smoke fixtures
├── pyproject.toml / uv.lock    Python package and frozen environment
├── package.json / pnpm-lock.yaml
│                               root checks and Web workspace
└── wrangler.jsonc              Worker/D1/R2 production bindings
```

Generated files under `contracts/` are never hand-edited. Change Pydantic
models or FastAPI routes, run `pnpm contracts:generate`, and commit the source
and generated diff together. D1 migrations are append-only after reaching
`main`. Local `.wrangler/`, virtual environments, vendored `python_modules/`,
build output, and secrets are ignored.
