# Production Delivery

## Status

**Complete.** Public infrastructure, exact-main delivery, scoped peer credentials,
the Registry black box, both peer target publications, and the final production
lifecycle journey are verified.

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
6. Registry checks run `31329108569` passed on source `08eb84f`, including the
   real Worker black box. Its workflow-run production delivery `31329161874`
   deployed the pinned source successfully. After recording the public origin
   as a repository variable, production run `31329229785` repeated the exact
   deployment and passed both configured public smoke requests.

The successful diagnostic deployment used exact source from remote main and
only overrode runtime compatibility arguments. The checked-in configuration
now carries the same pin and exact-main CD has replaced that diagnostic version.

## Publisher And Public Black Box

- D1 contains active `core-py-cd` and `client-web-cd` credentials scoped to the
  `inkcre` namespace. Their raw values were streamed directly into each peer's
  `INKCRE_EXTENSION_REGISTRY_TOKEN` GitHub Secret and were never printed or
  written to repository files.
- Both peer repositories expose the non-secret
  `INKCRE_EXTENSION_REGISTRY_URL` variable for the public origin.
- Temporary credential `production-smoke-20260810` published
  `inkcre/blackbox@0.1.0`, then was disabled.
- Public release, canonical manifest, and `remoteEntry.js` returned HTTP 200.
  The recomputed manifest identity equals
  `sha256:3d51fd949dacea5fcc9907328024eaeaf480b9d4ffd2b979857fb799d6a00f2a`,
  and the downloaded file SHA-256 equals its declared descriptor.
- The first acceptance assertion looked for a serialized `digest` property.
  The contract instead defines digest as the SHA-256 of canonical manifest
  bytes; recomputing the contract identity corrected the assertion without a
  service change.

## Completion

Both fresh peer worktrees completed their integrations and protected-main delivery.
Core preserved its no-runtime-download boundary through exact embedded-target admission;
Web loads digest-addressed Module Federation bytes. Final cross-peer evidence is owned by
[`work/14-peer-integration.md`](14-peer-integration.md) and
[`50-acceptance.md`](../50-acceptance.md).
