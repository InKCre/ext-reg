# Minimum Vertical Slice and Deferred Black-box Acceptance

## Accepted Product Slice

The minimum slice is not “render four steps.” It must prove that an installed
Twitter Release becomes durably useful through its real Web and Core
Distributions, while preserving the accepted config/state/Source authorities.

## Included Product Surface

1. The canonical Extension record has deployment-wide validated state.
2. The Core Host SDK exposes typed state access while Core/database remains the
   persistence and concurrency authority.
3. Twitter Core provides its setup projection, OAuth App/account/transaction
   commands, standalone callback page, bookmark Source composition and bounded
   readiness/Finish command.
4. Twitter Web contributes the four-step setup component.
5. `client-web` exposes the Extension-card action and popup shell after the local
   Web Distribution is enabled.
6. The Registry publishes both updated Twitter Distributions under one exact
   Extension Release version; the deployment consumes those native
   Distributions through their existing Host SDKs.

No generic wizard engine, OAuth broker, transaction service, notification
channel, new secret store, state table or Source ownership mechanism is part of
this slice.

## Primary Happy-path Journey

Starting from a fresh installed Twitter Release with the current Web Peer
enabled and no Core Peer enabled:

1. The Extension card offers **Setup**; opening it mounts Twitter's stepper in
   the `client-web` popup.
2. Prepare shows the exact callback URL and detects that Core is unavailable.
   The user explicitly enables Twitter on one suitable Core Peer.
3. The user enters an X OAuth App Client ID/Secret. Reopening the wizard shows
   the App as configured without returning the Secret.
4. Connect starts authorization and opens X in a separate window/tab. The Core
   callback completes on its own origin and displays a standalone terminal
   result. The still-open wizard advances only by polling its opaque transaction
   reference.
5. Account credentials and identity survive closing/reopening the wizard and a
   Core process restart. An alternate suitable Core Peer can read the same
   deployment state; the account is not owned by the callback Peer.
6. The user reuses or creates one bookmark Source, chooses its user-facing
   schedule/options, reviews the result and explicitly finishes.
7. Finish is idempotent, accepts or reuses the initial collection job, and the
   first bounded collection records at least one bookmark through the ordinary
   Source pipeline. Reopening setup reports the Extension as ready from durable
   facts.

## Required Behavioral Coverage

- Invalid, expired, replayed or mismatched OAuth callback state never replaces
  account state and yields a bounded transaction error.
- Closing the Web popup does not break an in-flight provider callback; reopening
  derives connected status from durable state.
- A failed reconnect leaves an existing working account untouched.
- Core unavailability leaves config, state and Source facts unchanged and makes
  readiness temporarily unavailable rather than incomplete.
- Repeating Source creation or Finish does not create duplicate default Sources
  or duplicate initial jobs.
- Disabling/re-enabling either Peer preserves deployment setup facts; disabling
  Web only removes the local entry, while disabling Core removes that command
  endpoint.
- Uninstall deletes the Extension record without inspecting or deleting Source
  records; the Source domain then exposes its existing unreachable-type behavior.
- Client Secret, PKCE verifier and tokens never appear in URLs,
  polling/setup projections, unauthenticated responses or logs. OAuth `state`
  appears only where the authorization-code protocol requires it—in the provider
  authorization and callback URLs—and is excluded from application logs and
  polling/setup projections.

## Deferred Black-box Acceptance

Black-box acceptance is explicitly deferred and owned by Sir. It is not a gate
for the implementation PRs in this task. The implementation still needs focused
unit, contract, integration and build evidence proportional to each repository,
but it must not create a provider simulator or real-X deployment workflow merely
to replace the deferred acceptance authority.

When resumed, black-box acceptance should select its own deterministic/external
strategy and use the behavioral outcomes above as input rather than inheriting a
test harness chosen prematurely here.

## Product-design Exit Gate

Product design is complete with this slice accepted and black-box acceptance
deferred. HLD now specifies exact state authority calls, Twitter Web/Core schemas
and routes, callback addressing, provider client seam, database migration,
repository changes, delivery sequence and verification commands. The resulting
[implementation plan](40-implementation-plan.md) is at Sir's review gate before
source work may start.

The authorized future implementation boundary ends when the relevant PRs are
ready for review. Merge, Release publication, deployment and black-box acceptance
remain outside this task unless separately authorized.
