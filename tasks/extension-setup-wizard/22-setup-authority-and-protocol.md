# Setup Authority and Protocol

## Corrected Security Boundary

The canonical deployment-wide `extensions.config` is the accepted authority
for Extension configuration, including Secrets. Authenticated Peers are inside
InKCre's chosen trust boundary and may read it through the shared database
protocol. Current Twitter Client ID/Secret fields already follow this model.

The earlier proposal for a second Core-only Extension secret store is rejected:
it would duplicate authority, add schema and lifecycle complexity, and impose a
security boundary the product has not chosen.

## Accepted Authority Split

### Extension config

Twitter's deployment-wide Extension config owns:

- OAuth App Client ID and Client Secret;
- other whole-Extension settings that are not Source-instance-specific.

Twitter Core commands validate and update this config through the Extension Host
SDK's existing config authority. Multiple Core deployments restore the same
values from the shared database. No Peer ID participates in their identity.

Schema/UI masking may improve accidental-disclosure UX, but does not change the
accepted authenticated-Peer access boundary. Credentials must still stay out of
URLs, unauthenticated responses and logs.

### Extension state

The canonical deployment-wide Extension state owns facts produced and evolved
by the Extension rather than declared by the user. For Twitter this includes:

- connected-account access and refresh credentials;
- restorable account identity and token metadata;
- OAuth `state`, PKCE verifier, expiration, status and error category for each
  short-lived authorization transaction.

The fact that some values are Secrets does not decide whether they are config or
state. Authorship and lifecycle do: Client ID/Secret are user-declared config;
OAuth account credentials and transactions are Extension-produced state. Both
remain inside InKCre's accepted authenticated-Peer trust boundary.

Extension state is not wizard UI progress. It must not contain `current_step` or
`setup_complete`. It persists across Core restart and Peer disable/re-enable,
and is shared by every Peer in the deployment. Source cursor and job state still
belong to the Source domain.

### Sources

Bookmark Source identity, schedule, config, cursor and jobs remain in the
existing Source domain. The wizard composes that domain and does not duplicate
Source facts inside Extension config.

## Twitter Setup Projection

The Twitter Core Distribution exposes one deployment-wide setup projection:

```text
TwitterSetup
  release/version
  command_endpoint_status
  oauth_app
    status: missing | configured | invalid
    callback_url
    client_id?
  account
    status: disconnected | connected | reconnect_required
    user_id?
    handle?
  bookmark_sources[]
    id, nickname, schedule, latest_job_status?
  readiness
    status: incomplete | ready | temporarily_unavailable
    blockers[]
```

This is a convenient validated projection over Extension config, Extension
state, runtime checks and Source facts. It contains no `current_step` or
manually stored `setup_complete`; the Web Distribution derives its display and
step.

## Twitter Commands

The Twitter-specific Core API provides these semantic commands. Their exact HTTP
routes and payload schemas are closed in
[Twitter Setup and OAuth Protocol](33-hld-twitter-protocol.md):

1. **Configure OAuth App** — validate Client ID/Secret and replace the relevant
   Extension config fields coherently.
2. **Begin account authorization** — create a short-lived state/PKCE transaction
   in Extension state and return the X authorization URL plus opaque transaction
   reference.
3. **Complete account authorization** — consume the callback, exchange the code,
   validate account/scopes, and atomically persist account credentials, identity
   and terminal transaction status in Extension state.
4. **Read authorization transaction** — return only its bounded polling
   projection: pending, succeeded, failed or expired.
5. **Disconnect/reconnect account** — explicitly clear or replace account state;
   reconfiguration never silently overwrites a working account.
6. **Create or select bookmark Source** — compose the Source authority
   idempotently and avoid duplicates on retry/reopen.
7. **Finish and start** — validate deployment facts and enqueue the initial
   collection job idempotently, returning the job reference and readiness.

One reachable enabled Core Peer processes a command, but the command mutates
deployment-wide config, state and Source authorities. It is a transport
endpoint, not the semantic owner of setup.
