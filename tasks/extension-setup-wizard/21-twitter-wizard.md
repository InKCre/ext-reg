# Twitter Wizard Proposal

## External Product Constraints

The current X OAuth documentation establishes these facts:

- An X App must have OAuth 2.0 enabled and its redirect URI must exactly match a
  callback URL configured in the Developer Console.
- Web applications are confidential clients and must keep their Client Secret
  within the application's accepted trust boundary. InKCre's boundary permits
  deployment-wide Extension config to contain it and authenticated Peers to
  read that config; URLs and unauthenticated surfaces remain outside the
  boundary.
- `offline.access` is required to receive a refresh token and restore user access
  without another interactive login.
- Bookmark lookup requires a user access token with `bookmark.read`; `tweet.read`
  and `users.read` support the returned posts and authenticated user. The current
  Extension does not need `bookmark.write` to collect bookmarks.

References:

- [X OAuth 2.0 Authorization Code with PKCE](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code)
- [X user access-token flow](https://docs.x.com/fundamentals/authentication/oauth-2-0/user-access-token)
- [X bookmarks lookup](https://docs.x.com/x-api/posts/bookmarks/quickstart/bookmarks-lookup)

## Accepted First-release Product Boundary

### OAuth App setup

The user registers an X developer account/App, configures the callback URL, and
enters the resulting Client ID and Client Secret as part of the setup wizard.
The wizard must provide the exact callback URL and guidance needed to finish
that external registration.

The credentials configure the deployment-wide Twitter Extension, not the Web
Peer that rendered the wizard. They are persisted in canonical Extension config
under the accepted authenticated-Peer security boundary. Account tokens and
identity produced by OAuth are persisted in canonical Extension state. The
wizard uses validated Twitter Core commands rather than inventing a second
persistence authority. Credentials still must not be placed in URLs,
unauthenticated responses or logs.

### Supported account path

The first release supports the official X OAuth backend only. Do not expose the
existing Twikit username/password/TOTP backend in this wizard. It is a separate,
less stable and higher-risk product path that would multiply credential and
recovery semantics before the official flow works end to end.

Request only `tweet.read users.read bookmark.read offline.access`. Add write
scopes in a later Extension version only when an accepted user-facing feature
actually writes bookmarks.

## Proposed Four-step Wizard

### Step 1 — Prepare

Explain what the Twitter Extension will do and the permissions it will request.
Then guide and inspect prerequisites:

- this Web Peer is already enabled and the setup component is loaded;
- at least one reachable Core Peer can run the same installed Twitter Release;
- Twitter is enabled on at least one suitable Core Peer, or the user explicitly
  authorizes enabling it there;
- the user has registered an X developer App with the exact callback URL;
- the user enters Client ID and Client Secret, which are submitted to Core and
  reported only as configured/not configured afterward.

If several suitable Core endpoints exist, one may be chosen as the command/OAuth
exchange endpoint. It does not scope setup to that Peer or assign permanent
ownership of the Source or its future jobs; Core's state/domain authorities
retain concurrency responsibility.

### Step 2 — Connect account

Show the exact scopes and start official X OAuth. After callback, display the
authenticated account identity and prove that its durable authorization can be
restored. Existing valid authorization is shown and may be reused; reconnect is
an explicit action rather than an automatic overwrite.

### Step 3 — Bookmark collection

List existing Twitter bookmark Sources. Let the user reuse one or create the
initial Source with the small set of user-relevant inputs:

- nickname;
- collection schedule;

The first release does not expose a newest-versus-history choice. It uses the
current bounded `full=false, result_limit=40` initial job. A later product
decision may add a history policy once collection semantics can support it
without misleading empty-state behavior.

The UI disables the creation action while its request is pending. An unlikely
duplicate Source from a repeated or concurrent request is acceptable; Source
identity and cursor state remain Core-owned domain facts.

### Step 4 — Review and start

Show the chosen account, Source, and schedule. Run a bounded readiness command
that verifies the durable authorization and required Source state. On explicit
Finish, enqueue the first collection job and close when Core accepts the
command. A repeated Finish may enqueue another Job; the wizard does not wait for
a complete bookmark history sync.

## Derived Resume Model

On every open, the Twitter setup component reads one Extension-specific setup
projection and resumes at the first unsatisfied condition:

```text
Core unavailable or disabled -> Prepare
OAuth App unavailable         -> Prepare / operator action
No restorable account         -> Connect account
No eligible bookmark Source   -> Bookmark collection
Ready facts satisfied         -> Review and start / already configured summary
```

Transient X or network failure is shown as an operational readiness error, not
by deleting already durable account or Source facts. Revoked/invalid refresh
credentials move the account back to “Reconnect required.”

## Intentional Non-goals

- No generic Host-owned wizard state machine.
- No Twikit setup path in the first release.
- No permanent Source-to-Core-Peer assignment.
- No second credential store alongside canonical Extension config.
- No wait for complete initial synchronization before the wizard may finish.
- No silent enablement of a Core Peer; enabling is an explicit user-authorized
  action within Prepare.
