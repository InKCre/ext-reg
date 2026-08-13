# Current-system Evidence

Evidence was read from each repository's `origin/main` on 2026-08-13. Exact
baselines were ext-reg `f8aebd0`, Core `63f57b2`, Client `4fdc083`, and
organization policy `81258c1`. The local
`client-web` and `core-py` working branches are not based on current main, and
the Core worktree also contains unrelated task-packet changes; this task did not
modify either worktree.

## Deployment and Web UI

- One deployment-wide `extensions` row stores canonical Extension Name, exact
  version, enabled Peer IDs, nickname, config, and config schema.
- That row currently has no Extension `state` field. `sources.state` is the
  existing deployment-durable precedent, used for cursors such as the latest
  collected item. Its current whole-object getter/setter does not provide an
  atomic cross-Peer mutation contract and should not be copied unchanged.
- `client-web` currently offers install, list, JSON config editing, exact version
  change, per-current-Peer enable/disable, and uninstall.
- `WebExtensionHost` resolves the exact Registry Release, checks the Web Host
  SDK range before fetching the Module Federation Distribution, runs its
  lifecycle, then commits the current Peer enablement.
- The Twitter Web Distribution exposes its default lifecycle module and tweet
  content component. Its lifecycle is effectively empty; there is no setup
  view, setup protocol, or setup status.

## Core Host and Twitter Runtime

- Core's Python Host installs and consumes a native wheel, validates its Host
  SDK association, and publishes its Extension-owned routes, Sources, and
  Resolvers only while the current Core Peer is enabled.
- Twitter's Core Extension config selects `official` or `twikit` and currently
  includes Twitter application credentials and alternative Twikit login
  fields.
- With the official backend enabled, the Extension publishes:
  - `GET /twitter/auth/authorize`
  - `GET /twitter/auth/callback`
  - `POST /twitter/bookmark`
- The callback exchanges the authorization code, fetches the Twitter user, and
  returns the token response.
- The resulting access token, refresh token, user ID, and handle live only on
  the in-process `OfficialAPI` singleton. Their intended persistence calls are
  commented out. Core disable closes and forgets the singleton.
- The bookmark Source cannot collect without this authenticated client. Source
  cursor state such as `latest_tweet_id` is already durable Source state, but
  OAuth credentials are not.

## Immediate Consequences

1. Installation is not setup.
2. Per-Peer enablement is not setup completion either: it only makes the Host
   runtime and routes available.
3. A successful OAuth callback currently proves only an ephemeral session, so a
   wizard that marks setup complete at that point would lie after restart.
4. Creating a bookmark Source is a distinct action from authentication and is
   necessary before scheduled collection can occur.
5. The setup experience crosses the Web Host, at least one Core Peer, the
   Twitter Web Distribution, the Twitter Core Distribution, and shared
   deployment state. The Registry is only the source of the two Distributions.

## Implementation-readiness Evidence

- The current Core installed-row projection is named `ExtensionState` even
  though it has no Extension-produced state. Its SQL store, runtime record,
  ExtensionBase config callbacks and exact PostgreSQL role/trigger boundaries
  were traced for the HLD rename and mutation plan.
- Core currently logs raw query parameters, and JWT middleware cannot exempt a
  dynamically contributed callback. Both exact change points are known.
- Client's `Client.list()` and authenticated request helper already provide the
  command-endpoint discovery transport; no new peer registry is needed.
- `InkDialog` 1.2.2 has the required `showCancel`, `showConfirm`,
  `closeOnScrim`, default slot and model event happy path; no dialog framework
  spike remains.
- Authlib 1.7.2 was executed in isolation with HTTPX mock transport to prove the
  planned S256/token/refresh path. PDM 2.27.0 resolved its production dependency
  graph in a temporary Core copy.
- The configured SSH Docker provider was reached successfully on 2026-08-13
  (Docker engine/client 28.5.2, Compose 2.40.3). It is the exact-image path for
  Client contract generation because this Mac has no local Docker CLI.
