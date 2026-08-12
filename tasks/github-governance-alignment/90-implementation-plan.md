# Simplified Implementation-ready Plan

## Authorization Boundary

This file is a plan, not implementation authorization. Task-packet edits are
allowed; code, workflows, GitHub settings, Cloudflare resources, credentials,
cross-repository changes, commits, pushes, PRs, destructive cleanup, and merges
retain their explicit authorization gates.

## Implementation Style

Use mature components on their documented happy paths: Pydantic/FastAPI for
typed product input, official GitHub Actions for checkout and artifact transfer,
GitHub contributor approval/Environments for trust, and Wrangler for Pages.
Do not replace those controls with custom archive, HTML/CSS, GitHub Deployment,
or Cloudflare client frameworks. Small repository-specific adapters remain
appropriate for catalog rendering and exact identity checks.

## Change Set A — Organization Policy Owner

Repository: `InKCre/.github`, on its own future `feat/` branch.

1. Edit `GOVERNANCE.md` to add `InKCre/ext-reg` to enforcement scope and add
   its profile: native Registry checks, isolated static Pages Preview, and
   protected-main Registry deployment.
2. Retain the existing rule that all external fork contributors require
   maintainer approval before secret-free Actions run.
3. Retain the same-repository/trusted-controller/Preview-Environment rule.
4. Verify Markdown and diff. No ext-reg implementation or remote setting changes
   occur in this branch.

## Change Set B — Static Review Document

### `src/inkcre_extension_registry/service/ui.py`

Change `extension_catalog_html` to accept keyword-only `api_origin` and
`noindex` options.

- `api_origin=None` preserves production relative links.
- A non-null origin must be canonical absolute HTTPS with no userinfo, path,
  query, or fragment; otherwise raise `ValueError`.
- Preview rendering uses `https://registry.inkcre.dev`.
- `noindex=True` adds `robots=noindex,nofollow` metadata.
- Existing escaping and empty/catalog rendering remain unchanged.

### `tests/fixtures/ui-preview.json`

Replace the obsolete SQL Preview seed with one object containing
`schema_version: 1` and the six current Extension summaries: GitHub, Learn
English, Mail, RSS/Atom Feeds, Telegram, and Twitter.

The builder rejects unknown top-level keys, wrong schema version, duplicates,
and invalid `ExtensionSummary` entries. This validates review input, not browser
content.

### `scripts/build_ui_preview.py`

Add a CLI requiring `--fixture`, `--output`, and `--api-origin`:

1. require a new or empty output directory;
2. validate the fixture;
3. render `extension_catalog_html(..., noindex=True)`;
4. write only UTF-8 `index.html`;
5. reject output over 64 KiB;
6. print a compact non-secret summary.

No source/digest manifest or HTML/CSS parser is added.

### Trusted tombstone and tests

- Add `.github/pages-preview-closed/index.html` and `_headers`.
- Extend `tests/test_ui.py` for preview origin, noindex, invalid origin,
  escaping, empty state, and unchanged production defaults.
- Add `tests/test_ui_preview.py` for fixture validation, deterministic output,
  one-file shape, and size bound.
- Rewrite stale Preview assertions in `tests/test_contracts.py`; remove
  Worker/D1/R2 and strict content-validator expectations.

## Change Set C — Workflows

### `.github/workflows/ci.yml`

1. Remove obsolete Preview Worker configuration, shared Preview D1/R2 mutation,
   Preview Worker deploy, and close cleanup.
2. Keep `pull_request`, `push main`, and manual checks; remove
   `pull_request_target` from CI.
3. Rename the aggregate public job to `ext-reg checks` while preserving frozen
   installs, `pnpm check`, local D1/R2 initialization, real Worker start,
   `uv publish`, Python install, and Module Federation smoke.
4. Add a PR-only exact-head artifact job after `ext-reg checks`: read-only token,
   exact head checkout, frozen install, static builder, exact one-file/regular/
   non-executable/64-KiB assertions, and one-day artifact named
   `ext-reg-ui-preview-<head-sha>`.
5. Fork runs remain secret-free and wait for GitHub's configured external-
   contributor approval before starting.

### `.github/workflows/pages-preview.yml`

1. Trigger `workflow_run` on completed `Registry checks`.
2. Default permissions read-only; use only `actions: read` and
   `pull-requests: read` before `environment: preview` supplies credentials.
3. Validate workflow name/path, `pull_request` event, success, repository,
   exactly one associated open PR, base `main`, same-repository head, and exact
   current head SHA. Reject forks.
4. Download exactly one unexpired `ext-reg-ui-preview-<sha>` artifact from that
   run into a task-specific temporary directory without executing it.
5. Require exactly one regular non-executable `index.html`, no other paths, and
   size <=64 KiB. Do not parse HTML/CSS.
6. Checkout trusted `github.workflow_sha`; copy only `index.html` to a new deploy
   directory; generate trusted `preview.json` containing schema version, PR
   number, and source SHA; generate trusted `_headers` with noindex, no-store,
   CSP, nosniff, and no-referrer.
7. Recheck PR/head immediately before mutation.
8. Deploy with immutable-SHA-pinned tooling to
   `vars.REGISTRY_UI_PREVIEW_PAGES_PROJECT`, branch
   `preview/ext-reg/pr-N`, exact commit hash. Read only the Preview Environment's
   `CLOUDFLARE_PAGES_API_TOKEN` and account variable.
9. Smoke immutable URL and alias for `preview.json`, SHA, HTML content type,
   noindex, and CSP; record URL in the job summary.
10. Use concurrency `pages-preview-ext-reg-N`, cancelling stale delivery.

Do not implement a changed-file classifier, content sanitizer, explicit GitHub
Deployment API lifecycle, or artifact deletion.

### `.github/workflows/pages-preview-cleanup.yml`

1. Trigger on `pull_request_target: closed` for `main` plus guarded manual PR
   number; default permissions read-only.
2. Verify a closed same-repository PR. Never checkout candidate code.
3. Use `environment: preview` and the same per-PR concurrency group; cleanup is
   non-cancellable.
4. Deploy the checked-in tombstone to the deterministic branch and verify it.
5. List Pages deployments as JSON for only the fixed project/exact branch;
   delete older deployments and retain the latest tombstone. Fail closed on
   malformed or ambiguous output.
6. Do not manage custom GitHub Deployments or manually delete Actions artifacts.

### `.github/workflows/production.yml`

1. Rename the public job to `ext-reg deployment` and keep manual
   exact-current-main authority.
2. Add `operation=verify|deploy`. Both fully check exact current `main` under
   `environment: production`; `verify` only reads Cloudflare identity/resources
   and public Registry state; `deploy` additionally migrates D1 and deploys.
3. Correct summary language to native-v2 Worker Version/data rollback.
4. Require a nonempty token without printing it.

All third-party Actions remain immutable-SHA pinned. `actionlint` is required.

## Change Set D — Operations And Historical Truth

1. Rewrite `docs/operations.md` Preview documentation to: approved fork
   CI/artifact only; same-repository exact-head artifact; trusted controller;
   fixed Pages project; protected Preview Environment; tombstone; artifact-only
   fallback.
2. Preserve correct rollback-window closure facts and native-v2 production
   rollback language.
3. Revise `tasks/extension-registry-mvp/work/15-native-cutover.md`: preserve
   cleanup evidence, mark per-PR Worker/D1/R2 rejected, and link this packet.
4. Record actual implementation/acceptance evidence here.

## Change Set E — Local Verification

Use a task-specific `mktemp -d`; remove only that directory afterward.

```bash
svc status --json
uv sync --frozen
pnpm install --frozen-lockfile
uv run pytest tests/test_ui.py tests/test_ui_preview.py tests/test_contracts.py
uv run python scripts/build_ui_preview.py \
  --fixture tests/fixtures/ui-preview.json \
  --output "$TASK_TEMP/preview" \
  --api-origin https://registry.inkcre.dev
test "$(find "$TASK_TEMP/preview" -type f | wc -l | tr -d ' ')" = 1
test -f "$TASK_TEMP/preview/index.html"
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 \
  .github/workflows/*.yml
pnpm check
git diff --check
```

## Change Set F — Git And PR Sequence

Each step needs its own explicit authorization.

1. Implement/verify `InKCre/.github` on a new `feat/` branch; commit, push, and
   open a separate PR.
2. Implement/verify ext-reg on a new `feat/` branch based on current `main`.
   Deliberately replace the abandoned `hotfix/preview-cleanup` topology.
3. Commit only follow-up files, push, and open a new draft PR.
4. Merge `.github` policy first; rebase ext-reg and rerun strict checks.
5. The introducing ext-reg PR cannot receive the new remote Preview because the
   controller is not yet on default branch. This is expected.
6. Once the new `ext-reg checks` succeeds, atomically replace only the old
   App-bound required context; re-read the full protection payload.
7. Do not merge automatically.

## Change Set G — External State

### GitHub

Apply reviewed full-state payloads and read them back:

1. merge commits false; squash/rebase true; automatic branch deletion false;
2. default workflow permissions read; Actions PR approval false;
3. fork approval `all_external_contributors`;
4. `preview` Environment protected-branches only, dedicated Pages token;
5. `production` Environment protected-branches only, dedicated production
   Worker/D1/R2 token;
6. variable
   `REGISTRY_UI_PREVIEW_PAGES_PROJECT=inkcre-extension-registry-ui-preview`;
7. strict App-bound `ext-reg checks`, preserving every other protection flag.

### Cloudflare

1. Create one Direct Upload project
   `inkcre-extension-registry-ui-preview`, production branch metadata `main`, no
   Git provider, custom domain, Functions, or data binding.
2. Create separate account-scoped Pages Write and Registry production tokens;
   never expose values.
3. Configure Environment secrets and audit metadata only.
4. Run production `operation=verify`; only then remove ext-reg from the shared
   organization Cloudflare token.

### Obsolete Preview resources

Keep old fixture-only Preview D1/R2 through canary. After acceptance, and only
with separate destructive authorization: verify exact identities; remove old
`REGISTRY_PREVIEW_*` variables; empty/delete only old Preview R2; delete only old
Preview D1; re-audit native-v2 production and `registry.inkcre.dev`.

## Change Set H — Black-box Acceptance

After controller code reaches `main`, open one bounded same-repository canary.

1. First head: prove merge-ref checks, exact-head artifact, controller identity,
   protected Preview Environment, immutable URL, alias, `preview.json`, headers,
   and absence of candidate credentials.
2. Prove the Environment's protected-branch rule accepts the default-branch
   `workflow_run` ref. If not, disable remote delivery and retain artifact-only
   review; do not weaken the Environment to accept PR refs.
3. Second head: prove stale cancellation and exact-SHA alias advancement.
4. Close: prove tombstone wins concurrency and older exact-branch deployments
   are removed.
5. External fork: prove workflow waits for maintainer approval; after approval,
   checks/artifact run without credentials and no remote Preview enters the
   Environment.
6. Inspect Pages source/provider, project/deployment/build usage, token metadata,
   no Functions/bindings/domain, and no Worker/D1/R2/production mutation.
7. Re-run production `/livez`, `/v1/extensions`, and Simple JSON 1.1 reads.
8. Audit GitHub settings, Environments, required check, Cloudflare state,
   artifacts/tombstones, obsolete resources, and local temporary files.

Unexpected paid/build quota or unacceptable provider authority disables Pages
delivery and leaves the one-day exact-head artifact. No alternate topology.

## End-to-end Order

1. Obtain implementation authorization only after fresh plan review passes.
2. Implement and locally verify both repositories without remote mutation.
3. With separate Git authorization, open/merge `.github`, then rebase ext-reg.
4. Open ext-reg; migrate required context only after new App-bound check passes.
5. Merge ext-reg after current-base checks and resolved conversations.
6. With external-state authorization, create project/tokens/Environments, apply
   settings, and run production read-only credential verification.
7. Run canary update/fork-approval/close/cost/production acceptance.
8. With destructive authorization, remove only obsolete Preview D1/R2/vars.
9. Record final governance, quota, residue, and production evidence.

## Closed Decisions

Artifact shape, trust split, approval policy, project/branch names, headers,
workflow events, permissions, Environment ownership, credential separation,
cleanup, fallback, migration order, and acceptance evidence are fixed. A proven
tool/API syntax correction may be made during implementation; a semantic change
returns to HLD review.
