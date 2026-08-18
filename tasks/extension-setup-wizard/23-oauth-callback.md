# OAuth Callback Proposal

## Rejected Alternative

`postMessage` from the Core callback to the Twitter Web wizard is rejected. It
would require the Core HTTP origin to know an allowed `client-web` origin,
window-opener topology and a browser message contract. That browser-level
coupling is not justified merely to auto-advance a setup step.

X currently documents authorization-code with PKCE and refresh-token as its
supported OAuth 2.0 grant types; it does not provide a device-code flow that
would remove the callback while retaining a native polling protocol.

Reference:
[X OAuth 2.0 Authorization Code with PKCE](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code).

## Accepted Decoupled Flow

Keep the OAuth callback inside the Twitter Core Distribution, but make it fully
standalone. The Twitter Web Distribution observes the Core transaction by
polling its ordinary Extension API.

```text
Twitter wizard modal remains open
  -> Begin authorization on one enabled Core command endpoint
  <- authorization URL + opaque transaction reference
  -> open X authorization in a separate window/tab
X redirects that window to the exact Twitter Core callback URL
Core validates state/PKCE, exchanges code, atomically updates extensions.state
Core marks transaction succeeded/failed in state and renders a standalone result page

Meanwhile, independently:
Twitter wizard polls transaction reference on the chosen Core endpoint
  -> pending | succeeded | failed | expired
  -> on succeeded, reload deployment-wide setup projection
  -> advance to the account summary
```

There is no communication from callback page to Web page. The callback page
does not know the Web origin, opener or popup. It simply tells the user that the
authorization completed and the window may be closed.

## Product Experience

- The wizard opens the authorization window and displays “Waiting for X…” with
  Cancel and Retry actions.
- It polls at a modest interval and has a visible expiration deadline; no
  permanent connection, SSE or WebSocket is required.
- Success normally advances without asking the user to click another button.
- If the authorization window cannot be opened, expose the authorization URL
  as a deliberate “Open X” action. The user may return to the still-open wizard.
- If the wizard, tab or browser closes, the OAuth callback still completes. On
  reopen, the wizard derives the connected account from `extensions.state` and
  resumes correctly, even though the transient transaction has expired.
- The result page may offer a plain close-window button or textual instruction;
  automatic close is optional and carries no product correctness.

## Boundary Rules

- Client ID/Secret and account tokens never appear in callback URLs or polling
  responses.
- The transaction reference is opaque, TTL-bound and single-use; polling is
  authenticated under the existing Peer/Core trust contract.
- X `state` is independently validated by Core and cannot be substituted with
  the public transaction reference unless HLD proves equivalent entropy and
  binding.
- Replay, mismatched state and expired flow fail without replacing existing
  credentials.
- Cancellation stops Web polling but does not rely on canceling an already-open
  X page. A later valid callback may still complete and will be reflected when
  setup is reopened.
- One Core endpoint starts, completes and reports a transaction. The resulting
  Extension state remains deployment-wide and future collection is not bound
  to that Peer.

## Why This Is the Smallest Coherent Choice

Polling is a Twitter Web target -> Twitter Core target dependency, which the
Extension already needs for setup commands. It does not add a Core callback ->
`client-web` deployment dependency. It uses the provider's supported happy path,
keeps the confidential exchange in Core, survives lost browser UI, and avoids
building a generic callback broker or real-time notification subsystem.
