# Pull-Request Previews

Pull-request Preview covers only the read-only Extension-list page. Registry
APIs, publishing, native Distribution consumption, installation, and runtime
behavior remain local black-box responsibilities.

Every pull request runs secret-free checks and emits a one-day bounded static
artifact. Fork pull requests receive no remote Preview authority. For an
eligible same-repository pull request, the trusted default-branch
`workflow_run` controller verifies the successful checks run, open PR,
same-repository origin, and exact current head before entering the protected
`preview` Environment.

The controller deploys only the bounded document to the fixed Cloudflare Pages
project `inkcre-extension-registry-ui-preview` on
`preview/ext-reg/pr-<number>`. Protected-main code adds source identity and
noindex, no-store, CSP, nosniff, and no-referrer policy. The Pages project has
no Git provider, custom domain, Functions, Worker, D1, R2, or production token.
Its links point to production public reads; it never claims to host candidate
Registry APIs.

Closing an internal PR deploys the checked-in tombstone, verifies the stable
alias, and deletes older deployments only for that project and branch. The
latest tombstone remains because Pages cannot delete the latest branch
deployment. If provider delivery or authority boundaries fail, disable remote
Preview and retain the short-lived artifact; do not create a second topology.
