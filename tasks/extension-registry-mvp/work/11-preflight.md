# Pre-implementation Mental Rehearsal

## Status

**Passed.** The intended changes have been simulated across source, CI/CD,
Registry state, deployment database, peer runtimes, failure handling, and
rollback. The implementation may begin without another product/HLD decision.

## Happy-path Sequence

```text
ext-reg main -> CI -> wheel/npm contracts + Worker production
  -> provision two inkcre publisher tokens

core main -> deterministic twitter zip + target manifest
  -> core image embeds same manifest/digest -> image push
  -> Registry append python-core-v1 -> core production deploy/migrate

web main -> relative-base twitter MF files + target manifest
  -> Registry append web-module-federation-v1 -> Pages production deploy

operator -> install inkcre/twitter@0.1.0 (zero bindings)
  -> enable browser peer -> Web target load/lifecycle -> Web binding
  -> enable core peer -> embedded Python target admission/lifecycle -> Core binding
  -> disable browser -> dispose/delete Web binding
  -> disable core -> close/unpublish/delete Core binding
  -> uninstall -> delete installation/config -> restart proves absent
```

## Publication And Race Rehearsal

- Blobs arrive before target association. A failure leaves only harmless
  content-addressed orphan bytes; no public target exists.
- Target association verifies every file and canonical manifest digest before one
  D1 transaction inserts the immutable slot.
- Two peer CDs may race on the same release. Distinct target keys both commit;
  first publication changes the release once and later publication is
  idempotently already-published.
- Re-running unchanged peer output produces the same executable target digest
  even when the enclosing application commit changes, because provenance is not
  part of that digest. The original accepted provenance remains audit truth.
- Changed bytes under the same version/key fail the CD with conflict. The
  publisher must bump Extension Version or deliberately add a new target key;
  Registry never overwrites.
- Web remote entry and chunks are associated by one manifest. No partially
  uploaded bundle can become selectable.

## Deployment And Lifecycle Rehearsal

- Install checks published metadata, inserts only one exact installation, and
  cannot accidentally start either peer.
- A disabled peer may lack a target; this does not block installation.
- Web enable resolves against its actual Platform Profile. Failed fetch, unknown
  condition, MF load error, lifecycle exception, or digest/path error performs
  cleanup and inserts no binding.
- Core enable can see a Registry Python candidate but rejects it unless the exact
  target digest is in its application image. Registry metadata alone can never
  authorize live Python download/execution.
- Core startup uses persisted binding plus embedded admitted manifest. It does
  not scan artifacts into installation state, so uninstall survives restart.
- Disable removes runtime effects before the binding. If the final database
  deletion fails, durable state remains enabled/not-running and startup retries;
  it is never silently reported disabled.
- The binding foreign key prevents uninstall while either peer is enabled. Once
  both bindings are gone, one transaction removes installation and config.

## Delivery-order Rehearsal

- Ext-reg ships first, so both peer locks/workflows reference immutable available
  runtime packages and a live API.
- Core ships before client because it owns new tables and published schema. Old
  web continues using the untouched legacy table during this interval; new tables
  do not break it.
- Core target may become public before the new image reaches Heroku. An early
  enable on the old process rejects the unadmitted digest and creates no binding.
- Web target may become public before the new Pages app. Old clients ignore it;
  appending never mutates existing bindings.
- Client CI generates types from the exact released core image, preventing a
  source-only schema guess.

## Credentials And External-state Rehearsal

- Raw publisher tokens are generated once, never printed into task docs or
  committed, hashed before D1 insertion, and stored separately in the two GitHub
  repositories. Either credential can be disabled independently.
- Cloudflare API credentials remain GitHub environment secrets; D1/R2 bindings
  expose no storage keys to code or publishers.
- Browser consumers need only the public Registry origin. Existing PostgREST/JWT
  local configuration is reused or reset through the production UI/Chrome; no
  secret is compiled into Pages.
- All remote resource names are resolved explicitly before destructive cleanup.

## Outage And Integrity Rehearsal

- Registry outage blocks publish/install/new enable/Web cold load without
  changing durable installation or binding state. Already-running hooks continue.
- Core may restart an existing exact binding from admitted image bytes even
  during Registry outage; this is allowed but not a public offline guarantee.
- R2 missing bytes produce a hard artifact failure. D1 metadata is not rewritten
  to hide it, and deployment state is unchanged.
- Target manifest and each returned file are content-addressed. Mismatched upload
  bytes are rejected at ingress; immutable route lookup cannot point to a mutable
  target key.

## Rollback Rehearsal

- Registry code rollback deploys an earlier Worker revision against the same
  append-only schema; it never rewrites releases. D1 migrations are additive.
- Core rollback leaves new tables intact and the legacy table untouched. The old
  core cannot run new bindings but does not corrupt them; re-deploying the new
  image restores operation.
- Web rollback shows the legacy UI and ignores new installation tables. The new
  deployment state remains recoverable by the new build.
- A bad target cannot be overwritten. Publisher yank blocks new selection; an
  already-bound deployment is explicitly disabled before uninstall or a future
  version change.
- Production acceptance runs only after all three exact-main deployments succeed,
  so rollback is not used to disguise a failed gate.

## Named Implementation Watchpoints

- Pin Node 22 for pywrangler; Node 26 is a proven failure.
- Keep executable target digest free of provenance to preserve idempotent CD.
- Fix core's current class-versus-string running-map lookup and route removal.
- Stop core artifact sync from recreating installed rows.
- Remove the Web `@inkcre/core` 0.0.0 share placeholder and use one coherent
  condition/profile value.
- Do not claim a lifecycle succeeded from HTTP status alone; verify database
  binding plus runtime effect in production.

## Gate Result

No unresolved scenario changes product behavior or HLD. Remaining uncertainty is
ordinary implementation/debugging risk, bounded by state-preserving failures and
the listed verification. Executable initialization is authorized to start.
