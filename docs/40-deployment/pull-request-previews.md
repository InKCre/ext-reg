# Pull-Request Previews

Pages hosts non-interactive samples of the catalog and Extension detail pages.
The build command invokes the same Python renderers used by the Worker, with
explicit fixture data. It preserves product controls and URLs and embeds the
rendered bodies as inert samples. The external sample selector is evidence UI,
not Registry navigation. The builder namespaces element IDs solely to embed
independent documents in one carrier.

Full product journeys run on the real Python Worker with isolated D1/R2 state,
as described in [Local Development](local-development.md). Preview limitations
must not introduce environment switches, alternative routes, hidden controls,
or preview renderers into product code. A fully interactive remote preview
would require the same Worker and isolated bindings; static Pages samples do
not establish that capability.

Every pull request runs secret-free checks. Fork pull requests receive no remote
Preview authority. For an eligible same-repository pull request, the trusted
default-branch `workflow_run` controller verifies the successful checks run,
open PR, same-repository origin, and exact current head. The protected Preview
job checks out and builds that head without provider credentials, then exposes
the Pages credential only to the delivery step.

The controller deploys only the bounded document to the fixed Cloudflare Pages
project `inkcre-extension-registry-ui-preview` on
`preview/ext-reg/pr-<number>`. Protected-main code adds source identity and
noindex, no-store, CSP, nosniff, and no-referrer policy. The Pages project has
no Git provider, custom domain, Functions, Worker, D1, R2, or production token.
The fixture contains sample published release descriptors. The builder owns its
64 KiB document bound, static navigation and inert behavior under `scripts/`;
the Worker package owns none of them. Controller-added headers disable scripts
and requests in this evidence document. The default-branch controller's legacy
`--api-origin` argument remains accepted during its transition, but it no longer
rewrites product links.

Closing an internal PR deploys the checked-in tombstone, verifies the stable
alias, and deletes older deployments only for that project and branch. The
latest tombstone remains because Pages cannot delete the latest branch
deployment. If provider delivery or authority boundaries fail, disable remote
Preview; do not create a second topology.
