# InKCre Extension Registry

The public control plane and native Distribution host for InKCre Extensions — owns Extension identity, the strict-SemVer Release lifecycle, publisher authority, and typed associations to normal Python packages and Module Federation Remotes.

`ext-reg` 是 InKCre 扩展的公共注册中心——负责扩展身份、Release 生命周期、发布者权威，以及 Python 包 / Module Federation Remote 的原生关联。

The public Registry origin is [`https://registry.inkcre.dev`](https://registry.inkcre.dev); its root page is a read-only Extension catalog. Python consumers use the Simple Repository API; browser consumers use the producer's native `mf-manifest.json`. Deployment installation, per-Peer enablement, and running state remain outside this repository.

The service runs as a Python Cloudflare Worker with D1 metadata and private R2 bytes.

## Quickstart

### Publish or inspect Extensions

The independent `inkcre-extension-toolkit` developer/CD distribution exposes `inkcre-ext` for inspecting native artifacts, publishing Releases, and building deterministic static preview facades:

```bash
pip install 'inkcre-extension-toolkit[cli]'
inkcre-ext --help
```

### Develop locally

```bash
uv sync --frozen
pnpm install --frozen-lockfile
pnpm check
```

`pnpm check` is the required local/CI gate. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## Documentation

- [Documentation index](docs/index.md)
- [Agent operating guide](AGENTS.md)
- [Local unit design](docs/30-unit-tdd/README.md)
- [Deployment and runtime](docs/40-deployment/README.md)
- Shared product truth Hub: [`InKCre/docs`](https://github.com/InKCre/docs)
