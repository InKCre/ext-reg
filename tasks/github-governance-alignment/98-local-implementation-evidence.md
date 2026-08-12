# Local Implementation Evidence

## Scope And Authority

Sir authorized the ext-reg-local implementation after the simplified plan and
independent review were complete. This batch changed only the ext-reg worktree:
UI rendering, fixture/build tooling, tests, workflows, Registry operations
documentation, and task evidence. It did not create or switch a Git branch,
stage, commit, push, open a PR, edit `InKCre/.github`, change GitHub settings or
secrets, create Cloudflare resources, deploy, clean remote resources, or merge.

## Implemented Topology

1. Every PR runs the public `ext-reg checks` job without Preview or production
   credentials.
2. A Pydantic-validated fixture renders one deterministic, noindex
   `index.html`; CI verifies it is one regular, non-executable file no larger
   than 64 KiB and retains it for one day.
3. External fork contributors remain subject to GitHub's configured maintainer
   approval. Approved forks get checks and artifact evidence only.
4. A same-repository successful PR run wakes a trusted default-branch
   `workflow_run` controller. It verifies the workflow path, repository, one
   open PR, base, current exact head, and artifact identity before entering the
   protected `preview` Environment.
5. The controller copies only the document, adds trusted `_headers` and
   `preview.json`, and uses the official Wrangler Action to deploy to the fixed
   Pages project on branch `preview/ext-reg/pr-N`.
6. Closing an internal PR runs only trusted controller code. It deploys a
   tombstone to the same branch, verifies it, and uses Wrangler's documented
   Pages list/delete commands to retire older deployments for that exact branch.
7. Production delivery now has an explicit read-only `verify` operation and a
   separate `deploy` operation, both against exact current `main` and the
   protected production Environment.

No HTML/CSS parser, changed-file classifier, generic sanitizer, custom GitHub
Deployment lifecycle, per-PR Worker, D1/R2 preview data plane, or manual Actions
artifact deletion was introduced.

## Local Verification

All commands ran on 2026-08-12 without remote mutation:

- `uv run pytest -q tests/test_ui.py tests/test_ui_preview.py tests/test_contracts.py`
  — 36 passed.
- `pnpm check` — generated contracts, format, Ruff, Pyright, 44 tests, Python
  sdist/wheel build, and Python Worker dry-build passed.
- `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
  .github/workflows/*.yml` — passed.
- Isolated `scripts/build_ui_preview.py` run — exactly one 4,424-byte
  `index.html` produced; the task temporary directory was removed.
- `git diff --check` — passed.
- `svc status --json` — healthy, adopted schema 2, installed/packaged 11.0.1,
  configuration and guidance current.

## Remaining Gates

Local checks cannot prove or authorize the external control plane. Before live
acceptance, the following reviewed steps remain:

1. update `InKCre/.github` enforcement/profile in its own branch and PR;
2. deliver this ext-reg change on a new reviewed branch/PR without merging it
   automatically;
3. apply and read back repository merge, Actions, fork approval, branch
   protection, and protected Environment settings;
4. create the fixed Direct Upload Pages project and separate least-privilege
   Preview/production tokens, then configure only their owning Environments;
5. merge the trusted controller before expecting remote Preview on a later
   same-repository canary;
6. run the canary through first head, superseding head, close tombstone, exact
   cleanup, fork artifact-only behavior, and Free-plan quota observation;
7. only after acceptance, separately authorize deletion of obsolete shared
   Preview D1/R2/settings; merge remains a separate decision.
