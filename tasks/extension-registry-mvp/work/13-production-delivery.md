# Production Delivery

## Status

**Current.** Public infrastructure and the Worker exist. Exact-main CD needs to
replay the verified compatibility-date correction before peer credentials are
seeded.

## Repository And Release Identity

- Public repository: `https://github.com/InKCre/ext-reg`.
- Verified source before the runtime pin: `854c76f388bb2d93345fd731c76cefc7fcf13f58`.
- Remote Registry checks run `31328402579`: passed, including a real
  `pywrangler dev` D1/R2 black box.
- Release run `31328453402`: passed.
- `@inkcre/extension-runtime@0.1.0` is published to GitHub Packages.
- GitHub release `v0.1.0` contains the Python wheel and source distribution.
- The release workflow now treats an existing version as valid only when its
  package surfaces are unchanged; changed package surfaces require a coherent
  version bump instead of an accidental republish.

## Cloudflare Production Resources

- Account: `5c21142473f771b49ee6da743900e842`.
- D1: `inkcre-extension-registry-production`
  (`7288f832-7def-4877-aef8-2e6f613458fe`, APAC).
- Private R2 bucket: `inkcre-extension-registry-production` (APAC).
- Worker: `inkcre-extension-registry`.
- Public origin: `https://inkcre-extension-registry.lanzhijiang.workers.dev`.
- The existing account-owned GitHub CI token retained its existing Worker/D1
  permissions and received only `Workers R2 Storage Read`, which Wrangler needs
  to validate the configured bucket. No raw credential was copied into task
  evidence or repository files.

## Delivery Findings

1. Production run `31328453408` applied the D1 migration but failed before
   Worker upload because the existing CI token could not read R2 bucket
   metadata. No Worker was partially deployed.
2. After the narrowly scoped permission correction, production run
   `31328883956` applied migrations and resolved both bindings, then failed
   Cloudflare startup validation with `Dynamic require of "fs" is not
   supported`.
3. A direct upload of Cloudflare's official four-line Python Worker reproduced
   the same error at compatibility date `2026-08-08`. This excluded FastAPI,
   Pydantic, D1/R2 bindings, and Registry source as causes.
4. The complete Registry deployed successfully at compatibility date
   `2026-07-28` with only the documented `python_workers` flag. Startup time was
   2332 ms and Cloudflare assigned version
   `e4e8b3dc-7b26-4cda-ac82-152985105531`.
5. Public `GET /livez` returned HTTP 200 and `{"status":"ok"}`.

The successful diagnostic deployment used exact source from remote main and
only overrode runtime compatibility arguments. The checked-in configuration
now carries the same pin so the canonical delivery remains exact-main CD.

## Next Evidence

1. Remote Registry checks pass on the compatibility-pin commit.
2. Exact-main production delivery deploys the same source and public `/livez`
   smoke passes.
3. Scoped publisher credential hashes are inserted into D1 while raw values go
   only to the two peer GitHub repositories.
4. A public black box publishes, resolves, downloads, and verifies one target
   through the production origin before peer integration begins.
