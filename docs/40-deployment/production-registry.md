# Production Registry

The canonical origin and Worker Custom Domain are
`https://registry.inkcre.dev`. Production uses the checked-in native D1 schema
and private R2 data plane. The rejected pre-native data plane and its rollback
window are gone; no generic target rows, blobs, credentials, or demo Releases
are migrated into the current plane.

The manual production workflow accepts an exact current-`main` SHA, rejects a
moved branch or unexpected binding identity, installs frozen dependencies,
runs the full contract, applies only checked-in migrations, deploys that exact
Worker, and smokes anonymous reads. It never creates or deletes Cloudflare
resources. The protected `production` Environment owns deployment credentials.

Because D1 cannot roll back R2, interrupted admission may leave unreachable
staging objects for bounded cleanup. Public byte routes still require readable
D1 lifecycle state. Never place publisher tokens in logs, task evidence, D1,
or workflow summaries.

Rollback is limited to deploying a previously verified Worker version that is
compatible with the current native data plane. The removed generic data plane
cannot be restored. After deployment verify `/livez`, Release descriptors,
Simple HTML/JSON, wheel metadata, Module Federation assets, CORS/cache/ETag,
retry/conflict behavior, yank transitions, and blocked reads. Record the
source SHA, workflow run, resource identities, migration state, and read-after-
write observations without credentials.
