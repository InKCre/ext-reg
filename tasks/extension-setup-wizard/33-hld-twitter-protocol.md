# HLD 3 — Twitter Setup and OAuth Protocol

## Core API

The enabled Twitter Python Distribution publishes these authenticated routes:

```text
GET    /twitter/setup
PUT    /twitter/setup/oauth-app
POST   /twitter/setup/oauth-transactions
GET    /twitter/setup/oauth-transactions/{transaction_id}
DELETE /twitter/setup/account
POST   /twitter/setup/bookmark-source
POST   /twitter/setup/finish
```

It also declares exactly one unauthenticated callback through the Core public
route contribution from [HLD 1](31-hld-callback-ingress.md):

```text
GET /twitter/auth/callback
```

Command response contract:

| Operation | Success | Relevant failures |
| --- | --- | --- |
| Setup projection | `200` projection | `409` runtime/config invariant, `503` transient dependency |
| Configure OAuth App | `200` refreshed projection | `409` reset confirmation required, `422` invalid input |
| Begin OAuth | `201` transaction reference/URL | `409` prerequisite missing, `503` transient provider preparation |
| Poll transaction | `200` bounded transaction projection | `404` unknown/pruned transaction |
| Disconnect | `204` | idempotent when already disconnected |
| Configure bookmark Source | `200` refreshed projection | `409` account/runtime prerequisite, `422` invalid schedule |
| Finish | `200` refreshed projection | `409` readiness/source mismatch |

All authenticated error responses use the existing Core JSON error contract and
bounded messages. The public callback renders fixed HTML: `200` for success,
`400` for denied/invalid/expired input, and `502` for a bounded provider exchange
failure. It never returns a JSON exception or provider response body.

The existing ad-hoc `/twitter/auth/authorize` and `/twitter/bookmark` endpoints
are removed in Twitter `0.2.0`. Setup commands replace them with one coherent,
resumable protocol.

## Setup Projection

`GET /twitter/setup` returns only Web-safe domain facts:

```json
{
  "extension": { "name": "inkcre/twitter", "version": "0.2.0" },
  "core": {
    "peer_id": "uuid",
    "callback_url": "https://core.example/twitter/auth/callback"
  },
  "oauth_app": {
    "status": "missing | configured | invalid",
    "client_id": "optional non-secret identifier",
    "client_secret_configured": true
  },
  "account": {
    "status": "disconnected | connected | reconnect_required",
    "user_id": "optional",
    "handle": "optional",
    "scopes": []
  },
  "bookmark_sources": [
    {
      "id": 1,
      "nickname": "Twitter bookmarks",
      "collect_at": { "day_of_week": null, "hour": 0, "minute": 0 },
      "latest_job": { "id": 1, "status": "pending | running | finished | failed" }
    }
  ],
  "readiness": {
    "status": "incomplete | ready | temporarily_unavailable",
    "blockers": []
  }
}
```

The projection never contains Client Secret, access/refresh token, provider
OAuth state, PKCE verifier or a stored wizard step. `callback_url` comes from
the selected Core's configured public `CLIENT_BASE_URL`; a missing/non-public
value is an explicit Prepare blocker.

Readiness is fact-derived. `ready` requires a configured current App, a
restorable connected account bound to it, one selected eligible bookmark Source
and an enabled Cron whose Job template carries the current account's
`authorization_id`. Finish enqueues an initial Job after establishing those
facts, but Job history is not a second readiness authority. Provider/Core
availability problems are `temporarily_unavailable`; they do not erase durable facts.
The GET projection itself performs no X network call. Begin/callback and Finish
are the bounded operational checks; ordinary collection remains responsible for
later provider failures.

## OAuth App Configuration

`PUT /twitter/setup/oauth-app` accepts:

```json
{
  "client_id": "...",
  "client_secret": "...",
  "confirm_account_reset": false
}
```

The command preserves unrelated Twitter config. Submitting the same credentials
is idempotent. Replacing credentials while an account or transaction exists
returns a conflict unless `confirm_account_reset` is true. A confirmed
replacement atomically updates config and clears the account and all OAuth
transactions; Sources are preserved.

The first setup release configures the official X backend and does not expose
Twikit credentials. Existing lower-level config fields may remain for backward
compatibility, but the setup projection and wizard do not promise that path.

`app_fingerprint` is a deterministic equality binding, not an authentication
credential: lowercase hex SHA-256 over UTF-8
`"inkcre-twitter-oauth-app\0" + client_id + "\0" + client_secret`. It lets any
Core Peer detect direct config replacement and prevents a token/transaction
created for one App from being used with another. The digest is never exposed by
the setup projection.

## Durable Twitter State

The Twitter state model is deployment-wide:

```text
TwitterState
  account?
    token                  Authlib token fields required for restore/refresh
    user_id
    handle
    scopes[]
    app_fingerprint
    authorization_id        opaque identity for this successful authorization
    connected_at
    reconnect_required
  oauth_transactions: map[transaction_id, OAuthTransaction]

OAuthTransaction
  provider_state
  pkce_verifier
  app_fingerprint
  redirect_uri
  status: pending | exchanging | succeeded | failed | expired
  created_at
  expires_at
  observe_until
  error_category?
```

Transaction ID and provider `state` are independently generated. Pending
transactions expire after ten minutes; terminal records remain observable for
another ten minutes. Starting a new transaction atomically marks every older
`pending` or `exchanging` transaction for the same App as failed with the
bounded category `superseded`. Consequently an older in-flight callback cannot
overwrite a newer user choice. Every mutation prunes expired records and keeps
at most eight recent transactions. These values are protocol bounds, not UI
progress.

Terminal transactions retain only their polling reference, status, timestamps
and bounded error category. Provider state and PKCE verifier are cleared on a
terminal transition; they are not needed for observation. A repeated callback
therefore receives the same bounded invalid/replayed result without recovering
or exposing the consumed secret material.

## Authlib Happy Path

Twitter uses `Authlib`'s `AsyncOAuth2Client` with HTTPX:

- authorization endpoint `https://x.com/i/oauth2/authorize`;
- token endpoint `https://api.x.com/2/oauth2/token`;
- scopes exactly `tweet.read users.read bookmark.read offline.access`;
- PKCE `S256` with a separately persisted verifier;
- confidential-client `client_secret_basic` token authentication;
- a ten-second HTTPX timeout for token and user-info requests;
- `fetch_token(... authorization_response=..., code_verifier=...)` in the
  callback;
- `update_token` to conditionally persist refreshed token state through the
  Core state authority.

A bounded temporary probe on 2026-08-13 exercised Authlib `1.7.2` with a real
HTTPX mock transport and proved S256 generation, Basic token authentication,
authorization-code exchange, automatic refresh and the async update callback.
PDM `2.27.0` also resolved `Authlib 1.7.2`, HTTPX `0.28.1`, cryptography and
joserfc into the current Core lock graph. Core and the Twitter wheel will both
declare the Authlib/HTTPX compatibility baseline because the Extension
consumer must not mutate Core-owned dependencies during enable.

## Begin, Callback and Poll

`POST /twitter/setup/oauth-transactions` requires configured App credentials and
a public callback URL. It supersedes an older non-terminal transaction, creates
one persisted pending transaction and returns:

```json
{
  "transaction_id": "opaque Web polling reference",
  "authorization_url": "https://x.com/i/oauth2/authorize?...",
  "expires_at": "timestamp"
}
```

The callback looks up the transaction by provider `state`. One
Core-authoritative mutation changes `pending` to `exchanging`; only that exact
transaction may subsequently commit. Network exchange and `/2/users/me` lookup
happen outside the database lock. A second conditional mutation commits account
token, identity, `connected_at` and `succeeded` together only when the same
transaction, App fingerprint and `exchanging` state are still current. A newer
Begin command changes the older status before this commit and therefore wins.
Every successful authorization also receives a new random `authorization_id`;
token refresh preserves it, while reconnect replaces it.

There is deliberately no exchange lease or reclaim protocol. Once an
authorization code may have been presented to X, a crashed process cannot prove
whether that one-use code was consumed. The transaction remains `exchanging`
until normal expiry and the user starts a new transaction. This is simpler and
more truthful than pretending the exchange can be recovered.

Invalid, mismatched, expired or replayed callbacks cannot replace a working
account. Provider failures become bounded categories, not raw exception text.
If the process dies while exchanging, the transaction expires/reconnects; the
existing account remains. The callback responds with fixed standalone HTML and
no redirect or browser messaging.

`GET .../{transaction_id}` returns only status, expiration and bounded error
category. It reports `exchanging` as pending to the Web experience. Web cancel
stops polling but does not mutate the provider transaction.

An Authlib refresh callback performs a conditional state mutation against the
same App fingerprint and previous token. A stale refresh cannot overwrite a
newer account. An `invalid_grant` observed against the still-current token may
mark `reconnect_required`; other transient failures preserve account state.
Twitter converts Authlib/HTTPX/provider exceptions to its bounded domain error
categories before they reach generic Core or Source-job logging; provider bodies,
authorization headers and token values are never used as exception messages or
job-state errors.

The official OAuth client is not a process singleton. Every provider operation
obtains fresh validated config/state, constructs one Authlib client, uses it for
that bounded operation and closes it. Multi-page collection may reuse the client
inside that one operation; a later operation reconstructs from durable state.
This follows Authlib's normal restore/close path and removes cross-Peer cache
invalidation, concurrent client replacement and stale startup-token problems.

The retained expert-only Twikit backend may keep its existing process-local
session cache, but only while a binding over its relevant fresh validated config
still matches; otherwise it is closed/replaced. That cache is never an
authority. A cleanup failure is reported as runtime unavailability but does not
roll back or overwrite an already authoritative database commit.

## Bookmark Source and Finish

`POST /twitter/setup/bookmark-source` accepts
`{source_id?, nickname, collect_at}` using the existing `CollectAt` shape. The
first release supports one initial bookmark Source:

- list/reuse every existing `extensions.twitter.bookmark.Source` in the setup
  projection;
- if the user chooses Create, Core's existing `SourceManager.create()` creates
  one ordinary Source row;
- the Web UI disables the action while the request is pending; rare duplicate
  Source rows are acceptable and remain manageable through the Sources surface;
- when `source_id` is supplied, the command validates and selects that existing
  Twitter bookmark Source without editing it;
- selecting an existing Source does not silently rename it.

Configuring the selection creates or updates one disabled Cron template. Finish
enables that template and enqueues a Job. A Cron failure does not roll back or
delete the Source row.

No newest-versus-history option is exposed in this release. The first job uses
the current bounded `full=false, result_limit=40` behavior. The bookmark
collector is corrected to handle an empty provider result without indexing the
first tweet.

`POST /twitter/setup/finish` validates the current account and selected Source,
performs one bounded authenticated `/2/users/me` check, updates/enables the
ordinary Cron template and calls the existing `CronManager.run_now()`. A repeated
Finish may enqueue another Job; that low-probability duplicate is acceptable.
The captured `authorization_id` remains in the Job template, so reconnect makes
old work ineligible before provider execution. The wizard does not wait for a
historical sync.

## Focused Verification

Tests use injected Authlib transport/time/random seams and real database
transactions. They cover configure/reset confirmation; S256/scopes;
restart-safe begin/callback/poll; superseding overlapping flows; exchange claim
and replay; expiry/pruning;
failure preserving a working account; conditional refresh; projection redaction;
cross-Peer config/token freshness, per-operation official clients and Twikit
cache replacement; standalone
callback; ordinary Source/Cron creation and Finish enqueue; reconnect ignoring
pre-connection jobs; reconnect racing Finish; and empty bookmarks.
They do not introduce a fake public X deployment or replace Sir's deferred
black-box acceptance.
