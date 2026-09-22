# Contributing

Use Python 3.13, PDM 2.28, Node 22, and pnpm 11.11.0. The Registry, Toolkit,
and Python Runtime use PDM's workspace support. Install frozen
dependencies and run the repository contract before opening a pull request:

Verification follows the organization-wide
[Verification and Test Policy](https://github.com/InKCre/.github/blob/main/TESTING.md). The commands below are this
repository's admitted local evidence.

```bash
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
pnpm check
```

Shared InKCre product truth and cross-unit contracts are mounted read-only from
`InKCre/docs`. Initialize the pinned reference after cloning:

```bash
git submodule update --init --recursive docs/_shared
```

Do not edit `docs/_shared/**` from this repository. The repo-root
`.agents/skills/edit-svc-shared-docs` wrapper points coding Agents to the
canonical Hub-first edit and isolated ref-bump workflow.

`pnpm check` verifies generated contracts, formatting, lint, types,
the Registry packages, and the real Pyodide Worker build. To update an executable
contract intentionally:

```bash
pnpm contracts:generate
pnpm check
```

Pull requests target protected `main`, preserve linear history, and include the
scope, verification evidence, risk, and rollback. CI and previews may publish
ephemeral evidence, but canonical packages and production deployment only come
from an exact successful current-`main` revision. Do not commit credentials,
local Wrangler state, generated dependency directories, or unrelated changes.

Package release intent uses the ecosystem-native release tool:

- Registry, Toolkit and Core Python Runtime changes use Towncrier. Create one
  fragment in the changed project's `.changes/` directory, for example
  `pdm run towncrier create --config towncrier.toml --dir toolkit 123.added.md`.
  The root `.changes/` belongs to the Registry service; `toolkit/.changes/` and
  `runtimes/core-py/.changes/` belong to those independently versioned packages.
- Client Web Runtime changes use `pnpm changeset`. Changesets creates the
  protected-main Version PR and updates its version and changelog.

The four versions are independent. A Python Version PR consumes pending
Towncrier fragments and updates only versions, changelogs and the workspace
lock. The Web Version PR consumes Changesets. Registry production deployment
remains separate from package publication even though the service has its own
version and changelog.

Every protected-main update reconciles both kinds of Version PR and publishes
prepared package versions. Python packages with pending fragments wait for the
Python Version PR instead of silently treating an existing tag as successful
publication. Existing releases are left unchanged.

Generated Version PR branches are checked through an explicit workflow dispatch.
GitHub deliberately prevents ordinary `GITHUB_TOKEN` pushes from recursively
starting `pull_request` workflows; the dispatch attaches the normal required
check to the generated head commit without bypassing branch protection.

Package publication runs static and generated-contract checks, then builds its
own release assets. The Registry database journey remains in repository CI; it
is not a dependency of Toolkit or Runtime publication.

Registry, Toolkit publication, Runtime publication and Cloudflare production changes are separate
privileged operations. Extension publishers install the independent
`inkcre-extension-toolkit[cli]` distribution, prepare typed associations with
`inkcre-ext prepare-release`, use PDM/Twine for wheels or
`inkcre-ext upload-module-federation` for a native Remote snapshot, and publish
the Release explicitly. Source revision and build identity should accompany the
prepare request.
