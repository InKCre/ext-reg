# Pull-Request Previews

Pull-request Preview covers the read-only catalog and Extension release details. Registry
APIs, publishing, native Distribution consumption, installation, and runtime
behavior remain local black-box responsibilities.

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
The fixture includes explicitly sampled published release descriptors. Catalog
links open details and version links select release views inside that same
HTML document, using URL fragments and CSS without scripts. Both surfaces
reuse the Worker's templates. The header marks the document as Preview; native
artifact links and Publisher controls are omitted because they require the
Registry service. No sample version is sent to a production endpoint.
The existing 64 KiB bound applies to the entire document.

Closing an internal PR deploys the checked-in tombstone, verifies the stable
alias, and deletes older deployments only for that project and branch. The
latest tombstone remains because Pages cannot delete the latest branch
deployment. If provider delivery or authority boundaries fail, disable remote
Preview; do not create a second topology.
