# InKCre Extension Registry

The public control plane and native Distribution host for InKCre Extensions.

The Registry owns Extension Name/Nickname, one strict-SemVer Release lifecycle,
publisher authority, and typed associations to normal Python packages and
Module Federation Remotes. Python consumers use the Simple Repository API;
browser consumers use the producer's native `mf-manifest.json`. Deployment
installation, per-Peer enablement, and running state remain outside this
repository.

服务使用 CPython、FastAPI / Jinja、Tortoise ORM 和 Neon PostgreSQL，私有文件继续存放于 R2，并通过 boto3 的 S3 接口访问。目录、详情、Publisher、API 与文件分发由同一个容器交付；没有独立前端部署。现有生产 Worker 的切换步骤见 [生产迁移](docs/40-deployment/production-registry.md)。

This repository also releases the independent
`inkcre-extension-toolkit` developer/CD distribution. Its `cli` extra exposes
`inkcre-ext` to inspect native artifacts, publish Releases, and build
deterministic static preview facades without depending on the Registry service
implementation.

The public Registry origin is [`https://registry.inkcre.dev`](https://registry.inkcre.dev).
Its root page is a read-only Extension catalog; package consumers continue to
use the native APIs described above.

## Local checks

```bash
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
REGISTRY_TEST_DATABASE_URL=postgres://registry:registry-check@localhost:5432/registry_check pnpm check
```

See the [documentation index](docs/index.md) for internal design and deployment
guidance. Contributor workflow lives in [CONTRIBUTING.md](CONTRIBUTING.md).
