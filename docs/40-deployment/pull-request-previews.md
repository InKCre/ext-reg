# Pull-Request Previews

A PR preview runs the same built Python Worker as production: catalog, Extension
details, Publisher, Registry API, Python index/files, and Module Federation
assets. It has its own Worker, D1 database, and private R2 bucket, all named
`inkcre-ext-reg-pr-<number>`. Its origin is the account's corresponding
`workers.dev` URL. No custom domain or production binding is inherited.

The existing `pnpm build` / `pnpm worker:build` commands build the application.
A separate runner uploads those modules with the same pinned Wrangler used by
pywrangler; it does not rebuild Python or introduce a frontend release unit.
The deployment template keeps the production compatibility date, flags, CSS/JS
module rules, and observability. Only resource bindings and origin differ.
Product routes, renderers, styles, and controls have no environment branches.

## Delivery authority

`registry-preview.yml` runs from the default branch after successful Registry
checks. Its controller verifies the workflow path, same-repository origin,
exact current head, and open PR targeting main. Forks receive checks only.
The candidate build has no deployment credentials. A separate delivery runner
checks out only the trusted controller and downloads this run's built modules
and SQL migrations. The controller writes the entire deployment configuration;
candidate build hooks, configuration, and commands never run with credentials.
It checks the current PR again after the build and concurrency queue.

The protected GitHub `preview` environment supplies:

- `CLOUDFLARE_ACCOUNT_ID`: target account variable (may override the repository
  variable when using a separate preview account).
- `CLOUDFLARE_PREVIEW_API_TOKEN`: a dedicated token with Workers Scripts Edit,
  D1 Edit, and Workers R2 Storage Write for that account. Do not reuse the
  production secret. Cloudflare's account-level control-plane permissions are
  not a per-Worker boundary; only the trusted controller receives this token.
  A separate account can provide stronger infrastructure isolation.
- `REGISTRY_PREVIEW_PUBLISHER_TOKEN`: a random token of at least 32 characters,
  used only for the isolated `demo` publisher namespace; it creates no sample
  Extensions or Releases. Reviewers obtain it through
  the operator, not logs, workflow summaries, or public artifacts.

The deployed application receives only its own DB, ARTIFACTS, and PUBLIC_ORIGIN.
It never receives Cloudflare credentials. This confines candidate application
code and namespace callers to that PR's data, while the controller retains
account-level deployment authority.

## State and retirement

Updates apply the candidate's checked-in migrations and retain that PR's data.
The controller configures the publisher credential independently of catalog data.
Deployment never creates Extensions, Releases, or sample artifacts, and its read
checks work with an empty catalog. Reviewers upload the actual Extensions they
want to evaluate through Publisher or the Toolkit. Temporary acceptance data is
removed after testing; it is not a retained preview dataset.

The deployment log records the source SHA, Worker Version, URL, and anonymous
read checks; identity is deployment evidence, not an endpoint or badge added to
the product.

Deploy and cleanup share one per-PR concurrency group without interrupting
active resource operations. Closing an internal PR runs the default-branch
cleanup controller; manual cleanup accepts only a closed eligible PR. Cleanup
replaces that PR's Worker with a small trusted retirement program, stopping
application writes. Using the native R2 binding, it drains batches of objects,
deletes the bucket, then deletes the Worker and D1 database. The temporary
program is deployment tooling and never ships in the Registry package. Wrangler
has no object-list command, and R2 requires an empty bucket before deletion;
this avoids separate S3 credentials or a product maintenance endpoint.
Interrupted cleanup is rerunnable, including resources created by a partially
failed deployment. A failed cleanup remains visible in Actions and must be
rerun; there is no silent expiry or production fallback.

The controller must first land on protected main before `workflow_run` can
activate it. During bootstrap an operator can use the same command with local
Wrangler authentication and an artifact prepared exactly as in the workflow:

```bash
pdm run python scripts/registry_preview.py deploy \
  --pull-number 33 --source-sha <exact-40-character-sha> --artifact /tmp/registry-worker
pdm run python scripts/registry_preview.py retire --pull-number 33
```

Set the account and publisher token through the environment. These commands
create/delete only deterministic preview resources; they are not production
commands. Retire only after closing the PR (or when deliberately resetting its
disposable acceptance data). The obsolete Pages workflows, static samples,
fixture carrier, and preview-specific renderer have been removed.
