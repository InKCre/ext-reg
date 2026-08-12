# Black-box Acceptance And Cleanup Evidence

## Outcome

All gates in `50-acceptance.md` passed on 2026-08-12. The accepted topology is
live, the disposable canary is closed, and the obsolete shared Preview data
plane has been removed. No production Registry data or production-v2 Cloudflare
resource was deleted or rewritten during this acceptance batch.

## Reviewed Delivery

- Organization governance change: `InKCre/.github` PR #24, squash merge
  `81258c1a7ec1e001b376b10bcf63930c2a527838`.
- Registry implementation: `InKCre/ext-reg` PR #8, squash merge
  `b3c19b064530d8d4d39c4ef7806818420c64fbf4`.
- Required status authority is the App-bound `ext-reg checks` context with app
  id `15368`; the context replacement preserved strict latest-base checking.
- Disposable Preview canary: `InKCre/ext-reg` PR #9, closed without merge after
  acceptance. Its source and delivery branches were deleted locally and from
  origin.

## Preview Journey

The first canary head `c4e6aa38c212a7cd0d3697caeb947a4bbf35f1d7`
passed Registry checks and deployed through trusted controller run
`31569228320`. The alias returned matching `preview.json`, the expected canary
content, `Cache-Control: no-store`, restrictive CSP, and
`X-Robots-Tag: noindex, nofollow`.

The second head `fae23e4857a37ca66debb3800410891b66f9799c` passed
checks and controller run `31569419552`. The same alias moved to the exact new
SHA and served only the v2 content. Re-running the first-head check caused
controller run `31569641331` to fail at exact-head identity resolution before
deployment. The alias remained on the second SHA and content.

Closing PR #9 triggered cleanup run `31569675710`. It replaced the alias with a
trusted noindex/no-store tombstone and deleted both older PR #9 candidate
deployments. A post-cleanup Cloudflare listing showed exactly one tombstone for
`preview/ext-reg/pr-9` and one for the earlier implementation PR branch
`preview/ext-reg/pr-8`; no live candidate deployment remained.

The fixed project is `inkcre-extension-registry-ui-preview`. It has no Worker,
D1, R2, Function, custom domain, or per-PR project. The Preview Environment owns
only `CLOUDFLARE_PAGES_API_TOKEN`, backed by the active account token
`inkcre-ext-reg-pages-preview` with Pages Write only.

## Production Authority

The production Environment is restricted to protected branches and owns only
`CLOUDFLARE_API_TOKEN`. Its active token is
`inkcre-ext-reg-production`, limited to:

- D1 Write;
- Workers R2 Storage Write;
- Workers Scripts Write;
- Zone Read;
- Workers Routes Write.

Production workflow run `31570374641` used operation `verify` against exact main
`b3c19b064530d8d4d39c4ef7806818420c64fbf4`. It verified source and resource
identity, read the production D1/R2/Worker authority, ran anonymous production
smoke checks, and recorded evidence without applying migrations or deploying.
The run passed. Cloudflare subsequently reported use of the dedicated token.

An initially generated candidate token whose one-time dialog was inadvertently
rendered into diagnostic output was treated as compromised: it was never stored
in GitHub or used by a workflow and was deleted immediately. A fresh token was
transferred directly through the browser clipboard into the encrypted
Environment secret without exposing its value. The ext-reg repository was then
removed from the selected repositories of the shared organization
`CLOUDFLARE_API_TOKEN`; the remaining selected repositories are client-web,
docs, and ui.

## Live Governance Read-back

- merge commits disabled; squash and rebase enabled;
- Actions default token `read`; Actions cannot approve pull requests;
- external-fork workflow approval policy `all_external_contributors`;
- protected `main`: admins enforced, linear history, strict checks, resolved
  conversations, no force push, no deletion;
- required check: `ext-reg checks`, app id `15368`;
- Preview and production Environments: protected branches only;
- Preview secret: `CLOUDFLARE_PAGES_API_TOKEN`;
- production secret: `CLOUDFLARE_API_TOKEN`;
- repository variables reduced to `CLOUDFLARE_ACCOUNT_ID`,
  `INKCRE_EXTENSION_REGISTRY_URL=https://registry.inkcre.dev`, and
  `REGISTRY_UI_PREVIEW_PAGES_PROJECT`.

## Rollback-window Cleanup

After the canary passed, these exact obsolete resources were deleted:

- D1 `inkcre-extension-registry-preview`
  (`0af2f7f1-df27-4bde-bcac-fe50e717a0ae`);
- R2 bucket `inkcre-extension-registry-preview`;
- repository variables `REGISTRY_PREVIEW_D1_DATABASE_ID`,
  `REGISTRY_PREVIEW_D1_DATABASE_NAME`, `REGISTRY_PREVIEW_R2_BUCKET_NAME`, and
  `REGISTRY_PREVIEW_WORKERS_SUBDOMAIN`.

Read-back retained D1/R2 `inkcre-extension-registry-production-v2` and showed no
remaining Registry Preview D1 or R2 resource. Temporary feature/canary branches
in ext-reg and the organization-governance branch in `.github` were deleted
after their PRs were merged or closed.

## Final Service And Repository Evidence

- `https://registry.inkcre.dev/livez` returned `{"status":"ok"}`.
- `/simple/` returned PEP 691 API 1.1 and six Python projects.
- `/v1/extensions` returned six canonical names, including
  `inkcre/twitter`.
- `/` returned the Extension-list Web UI with `Cache-Control: no-store`.
- `pnpm check` passed generated contracts, formatting, Ruff, Pyright, 44 tests,
  sdist/wheel build, and Python Worker dry-build.
- `svc status --json` reported healthy, schema 2 adopted, installed/packaged
  SVC 11.0.1, and current configuration/guidance.
- `git diff --check` passed and both ext-reg and `.github` main worktrees were
  synchronized with origin.
