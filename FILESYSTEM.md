# Filesystem

```text
.
├── contracts/                  generated native JSON Schema, OpenAPI, revision
├── docs/                       durable navigation and operations
├── migrations/                 native D1 initial schema
├── scripts/                    contract generator and Worker smoke client
├── src/
│   ├── worker.py               Cloudflare top-level entry shim
│   └── inkcre_extension_registry/
│       ├── contracts/          common Release and typed association models
│       ├── service/            catalog UI, admission, Simple/MF, D1/R2 adapter
│       ├── cli.py              native association/lifecycle publisher CLI
│       ├── client.py           small Release control-plane HTTP client
│       └── worker.py           R2 raw-byte routing and ASGI bridge
├── tasks/                      active disposable delivery control surface
├── tests/                      contract, archive, service, and lifecycle tests
├── pyproject.toml / uv.lock    Python package and frozen environment
├── package.json / pnpm-lock.yaml
│                               root checks and pinned Wrangler tooling
└── wrangler.jsonc              Worker/D1/R2 binding configuration
```

Generated files under `contracts/` are never hand-edited. Change Pydantic
models or FastAPI routes, run `pnpm contracts:generate`, and keep the source and
generated diff together. The clean native cutover treats `0001_registry.sql` as
a new database's initial schema; it is not applied as an in-place transform of
the rejected generic schema. Local `.wrangler/`, virtual environments, vendored
`python_modules/`, build output, and secrets are ignored.
