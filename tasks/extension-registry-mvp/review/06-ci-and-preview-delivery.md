# Review Batch 06 — CI And Preview Delivery

## Scope

Repair the first Core Draft PR checks against the actual frozen environment and
add a cognitively small Registry catalog preview path without weakening the
production cutover boundary.

## Diagnosis And Disposition

Core's local virtual environment predated its regenerated lock. GitHub therefore
ran Ruff 0.16.2 while the earlier local proof ran Ruff 0.14.10. The new formatter
required one expression rewrite and made one `S603` suppression obsolete. The
portable database job also revealed that readiness treated the new
`set_extension_peer_enabled` RPC as the only protocol function, even though the
protected history intentionally moves `update_updated_at_column` into the same
schema. The fix changes only the expected inventory and formatting; it does not
alter migration or runtime database behavior. Pinned PDM 2.27.0 now completes
the full Core contract with 217 tests and zero type diagnostics.

The next Portable run reached a second pre-existing probe mismatch: the database
guard intentionally raises SQLSTATE `23514`, which PostgREST maps to HTTP 400,
while the black-box script expected 409 and exited before disabling its probe
Extension. The transport assertion now expects 400; Core's own semantic conflict
responses remain 409. GitHub then completed PostgREST read/write, deterministic
reset, web artifact, schema export, and fresh restore successfully.

The first preview design considered per-PR Cloudflare resource creation. That is
rejected for this MVP: it would turn a read-only catalog preview into a resource
orchestration and cleanup system. The accepted topology is one dedicated preview
D1/R2 pair plus one dedicated preview Worker. Each same-repository PR receives
an immutable Worker Version and stable `pr-<number>` alias after the full Registry
contract passes. The workflow contains no resource-creation command, no
production Custom Domain, no production binding name, and no publisher
credential. An idempotent `inkcre/preview` fixture makes the catalog non-empty.

## Authorization And Remote Boundary

Sir authorized the CI fixes, preview workflow, commits, pushes, and the isolated
preview provisioning handshake. A dedicated account-owned Cloudflare token now
has only `D1 Write` and `Workers Scripts Write`; it is stored as the existing
GitHub organization Actions secret with selected-repository access that includes
`ext-reg`. The preview resource pair is distinct from production:

- D1 `inkcre-extension-registry-preview`
  (`0af2f7f1-df27-4bde-bcac-fe50e717a0ae`)
- R2 `inkcre-extension-registry-preview`

The account ID is an organization variable; the preview D1/R2 names, D1 ID, and
Workers subdomain are repository variables. The first rerun proved those plain
variables reached the job but retained the original event's empty secret
snapshot, so the next pushed PR head is the activation proof. Production
resources, `registry.inkcre.dev`, publisher data, releases, merges, and
demo-database cutover remain unchanged.

## Verification

- Core pinned PDM 2.27.0 full contract: 217 tests, Ruff/format clean, Pyrefly zero diagnostics.
- Core GitHub checks: Hermetic repository contract and Portable peer database runtime pass at `5812589`.
- Registry full contract: 31 tests, generated contracts, package build, and Worker dry build.
- GitHub workflow validation: actionlint 1.7.12 and repository isolation assertions pass.
- Registry GitHub checks pass; the original unconfigured run skipped preview.
- Rerun `31458261892` reached the preview job with the isolated bindings but
  failed closed before D1 mutation because its original event snapshot had no
  token. A fresh pull-request event is required to read the new organization
  secret.
- Preview SQL is idempotent and contains no credential or Distribution bytes.
- Git diffs pass whitespace checks; unrelated Core `uv.lock` remains untracked and uncommitted.
