# Registry Web

Registry Web is a presentation surface of the Python Worker. FastAPI reads the
existing Registry repository and renders autoescaped Jinja templates. Small
browser enhancements cover theme selection, copying an Extension ID, and the
publisher workspace. There is no separately deployed frontend or browser
framework runtime.

## Public discovery

`/` lists published Extensions with server-rendered name search and publisher
filtering. Search is a case-insensitive substring of the canonical name or
nickname; filtering combines with search. An empty Registry and empty search
results have different recovery actions. The page remains useful without JavaScript.

`/explore/{namespace}/{name}` displays published releases and their admitted
native distribution descriptors. Versions are sorted by SemVer; the default
selection is the highest stable version, or the highest pre-release if there
is no stable release. The optional `version` query selects an exact published
version. Missing or withdrawn versions return a human-readable 404. Existing
`/v1`, `/simple`, `/packages`, and Module Federation asset paths retain their
machine-facing semantics.

The UI does not invent descriptions, popularity, trust badges, compatibility
verdicts, installation state, or download counts that Registry does not own.
Package inspection and copying an ID do not install or activate an Extension.

## Publisher workspace

`/publish` connects a namespace credential kept only in the current page's
memory. A reload, navigation away, or disconnect clears it. Credentials are
sent in Authorization headers to the same origin, never in URLs, local storage,
HTML, or logs. Only the theme preference is persisted in local storage.

`GET /v1/publisher?offset=0` authenticates through the existing namespace
credential dependency and returns only that namespace's releases, including
preparing, withdrawn, and operator-blocked releases. Pages contain at most ten
records to bound the existing descriptor reads within the D1 query budget.
`next_offset` indicates another page; concurrent publication can shift this
non-snapshot listing, and Refresh reloads current state. Private responses,
including rejected credentials, are not cached. Per-distribution uploaded flags
come from the admitted files/manifest association, not a browser assumption.

The Web release form calls the existing prepare endpoint, uploads a Module
Federation ZIP through the existing multipart endpoint, and asks for a separate
publication decision. Failed preparation or upload keeps the form available
for correction; published bytes and metadata remain immutable. The workspace
also withdraws and restores releases through existing lifecycle endpoints.
A failed refresh after a successful mutation is reported separately from a
failed mutation. Timeout messages tell publishers to check state before retrying.

Python releases continue to use the Developer Toolkit/native Python upload
protocol. They appear in the same workspace for publication and lifecycle
management. Namespace and credential issuance remains an operator responsibility.

## Design ownership

`@inkcre/ui-web` is the existing package released by the sibling `design`
repository (`InKCre/ui`). Registry installs the package from its immutable public release commit
using pnpm’s Git subdirectory support, and imports its public Sass styles, token maps,
and functions. This avoids requiring private GitHub Packages access in public CI;
compiled Vue exports are not part of this consumer contract. Colors, typography families, and common spacing/radius vocabulary
remain design-owned; `web/registry.scss` owns Registry page composition. There
is no Registry copy of the token source or a competing design package.

`pnpm web:build` compiles the pinned package and local Sass into the committed
`service/static/registry.css`. `pnpm web:check` compares it to a fresh compilation
and checks browser JavaScript syntax. Committing generated CSS makes Python wheel
and static-preview builds self-contained; it is never edited manually. Wrangler
Text rules explicitly include CSS and JavaScript in the Python module filesystem.
The same HTML renderer supplies the existing read-only Pages catalog preview.
