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

The first preview design considered per-PR Cloudflare resource creation. That is
rejected for this MVP: it would turn a read-only catalog preview into a resource
orchestration and cleanup system. The accepted topology is one dedicated preview
D1/R2 pair plus one dedicated preview Worker. Each same-repository PR receives
an immutable Worker Version and stable `pr-<number>` alias after the full Registry
contract passes. The workflow contains no resource-creation command, no
production Custom Domain, no production binding name, and no publisher
credential. An idempotent `inkcre/preview` fixture makes the catalog non-empty.

## Authorization And Remote Boundary

Sir authorized the CI fixes, preview workflow, commits, and pushes. The workflow
definition is safe to merge while infrastructure is absent: a configuration job
reports missing repository variables and skips deployment. Activating it later
requires a dedicated preview D1/R2 pair, account/subdomain variables, and a
least-privilege Cloudflare token. Those provisioning and secret-writing actions
have not occurred in this batch. Production resources, `registry.inkcre.dev`,
publisher data, releases, merges, and demo-database cutover remain unchanged.

## Verification

- Core pinned PDM 2.27.0 full contract: 217 tests, Ruff/format clean, Pyrefly zero diagnostics.
- Registry full contract: 31 tests, generated contracts, package build, and Worker dry build.
- GitHub workflow validation: actionlint 1.7.12 and repository isolation assertions pass.
- Preview SQL is idempotent and contains no credential or Distribution bytes.
- Git diffs pass whitespace checks; unrelated Core `uv.lock` remains untracked and uncommitted.
