# InKCre Extension Registry

The public control plane and native Distribution host for InKCre Extensions.

The Registry owns Extension Name/Nickname, one strict-SemVer Release lifecycle,
publisher authority, and typed associations to normal Python packages and
Module Federation Remotes. Python consumers use the Simple Repository API;
browser consumers use the producer's native `mf-manifest.json`. Deployment
installation, per-Peer enablement, and running state remain outside this
repository.

The service runs as a Python Cloudflare Worker with D1 metadata and private R2
bytes. It does not publish a generic target manifest or a shared Runtime/API
package.

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
pnpm check
```

See the [documentation index](docs/index.md) for internal design and deployment
guidance. Contributor workflow lives in [CONTRIBUTING.md](CONTRIBUTING.md).
