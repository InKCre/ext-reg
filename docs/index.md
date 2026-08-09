# Documentation

This directory is the navigation root for durable Extension Registry knowledge. Shared InKCre product truth and cross-unit contracts remain owned by the `InKCre/docs` Hub; active work remains under `tasks/`.

## Current Navigation

- Active MVP control surface: [`tasks/extension-registry-mvp/packet.md`](../tasks/extension-registry-mvp/packet.md)
- Repository architecture: [`ARCHITECTURE.md`](../ARCHITECTURE.md)
- Filesystem ownership: [`FILESYSTEM.md`](../FILESYSTEM.md)
- Production operations: [`operations.md`](operations.md)
- Registry-local durable documents will be admitted only when schemas, code, tests, configuration, or automation cannot preserve the required contract clearly enough.

<!-- svc:begin navigation sha256=01d8643023a40533a997a67c70e920bb0ff0056081d2d18bec59e47324318152 -->
## SVC

This project uses the local Sustainable Vibe Coding CLI. Query framework guidance when it is needed instead of copying framework documents into this repository.

- Use `svc lookup --keyword "<need>"` to find relevant guidance, then `svc lookup --name '<exact-path-regex>'` to read an authoritative document.
- Use `svc status` before broad process changes. If the installed corpus is newer than the adopted version in `svc.json`, read its migration guidance before `svc adopt`.
- Treat all unmarked project instructions and documentation as consumer-owned.
<!-- svc:end navigation -->
