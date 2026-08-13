# HLD 1 — OAuth Callback Ingress

## Current Constraint

Core's current `JWTMiddleware` runs before route dispatch and rejects every
request without a Peer JWT except a hard-coded health/docs list. X redirects a
browser with `code`/`state` query parameters and cannot attach InKCre's Peer JWT.
FastAPI route dependencies therefore cannot make the existing Twitter callback
reachable by themselves.

The current request logger also records raw query parameters, which would leak
the authorization code and OAuth state into logs.

## Rejected Shapes

- Do not hard-code `/twitter/auth/callback` in Core middleware; Core must not know
  a first-party Extension's route.
- Do not introduce a Core-wide OAuth callback broker; OAuth remains Twitter
  protocol.
- Do not relay through `client-web`, `postMessage`, opener state or Web origin.
- Do not put a Peer JWT in a callback URL.

## Core Extension API

Add one generic route-visibility contribution, defaulting to none:

```python
class PublicHTTPRoute(BaseModel):
  method: Literal["GET", "POST"]
  path: str  # exact Extension-relative path, no parameters or wildcard

class ExtensionBase:
  @classmethod
  def public_http_routes(cls) -> tuple[PublicHTTPRoute, ...]:
    return ()
```

Twitter declares only `GET /auth/callback`. During startup, `ExtensionHost`
combines the Extension runtime prefix with that relative path, verifies that one
published FastAPI route has the same exact method/path, and acquires a claim in a
Core-owned process-local `PublicHTTPRouteRegistry`. `JWTMiddleware` bypasses Peer
JWT validation only when the exact `(method, path)` is actively claimed.

The registry is lock-protected, rejects a second owner of the same method/path,
and returns an idempotent owner-token claim handle. It is policy state for one
Core process, not deployment state and not persisted in the database.

Startup first publishes the Extension routes, verifies an exact route match,
then acquires the public-route claim. A failed verification or conflicting claim
rolls back both the route publication and every other startup contribution. The
claim is never visible before the route it authorizes and never survives that
route.

The claim is part of `ExtensionPublication`: startup rollback, disable and
shutdown remove it together with the route. No prefix, regex, arbitrary callback
function or Extension-managed middleware is exposed. Disabling Twitter during a
pending authorization makes the callback unavailable; the transaction expires
without changing account state.

This is a Core Extension API feature, not a setup/OAuth API. It lets a running
Extension publish an exact unauthenticated inbound while Core retains routing,
lifecycle and authentication-policy authority.

This shape is the implementation baseline. It introduces no callback broker or
Twitter hard-code and is fully withdrawn with the Extension publication.

## Callback Address and Provider Client

The selected Core Peer derives the callback URL from its authoritative
`CLIENT_BASE_URL`/registered `clients.rest_api_url` plus
`/twitter/auth/callback`. Setup fails with a prerequisite blocker when that Core
has no public base URL. The wizard displays this exact URL for X App registration;
it does not infer a callback from the Web origin.

Twitter uses Authlib's `AsyncOAuth2Client` happy path rather than manually
constructing token requests:

- `create_authorization_url(..., code_verifier=...)` with
  `code_challenge_method="S256"`;
- persist the returned OAuth state and verifier in Extension state;
- reconstruct the client after callback and call `fetch_token(...,
  authorization_response=..., code_verifier=...)`;
- use Authlib's token/refresh support and persist refreshed tokens through the
  Core state authority.

Authlib documents this explicit save/restore flow for async HTTPX clients and
PKCE. X requires exact callback matching, supports S256, and gives an
authorization code only a short exchange lifetime, so the callback performs the
exchange immediately rather than enqueueing it.

References:

- [Authlib async OAuth 2 client and PKCE](https://docs.authlib.org/en/1.7.1/oauth2/client/http/)
- [X OAuth 2 authorization code with PKCE](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code)
- [X App callback requirements](https://docs.x.com/fundamentals/developer-apps)

## Logging and Response

Core stops logging raw query strings for all requests; method, path, trace ID,
status and duration remain. Twitter maps provider/callback failures to bounded
categories before logging. The callback returns a small standalone HTML result
page containing no code, state, token, Web origin or redirect-to-Web behavior.

## Verification Boundary

Focused Core tests must prove exact route matching, JWT enforcement on adjacent
paths/methods, claim cleanup on rollback/disable, callback reachability without a
JWT, query-value absence from logs, and account-state preservation on invalid or
replayed state. Twitter error tests also prove provider response bodies and token
values do not reach generic request logs. These are repository checks, not the
deferred black-box journey.
