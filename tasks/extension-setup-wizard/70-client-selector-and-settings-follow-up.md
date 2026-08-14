# Client Selector and Client Settings Follow-up

## Status

Source implementation is complete and locally verified on the Client PR #68
branch. Core, Registry, database-contract, commit, push and remote delivery
remain out of scope.

## Acceptance Finding

The current Extensions page reports only a deployment-wide enabled count while
its switch always controls the current browser Client. During preview
acceptance, the current Web Client was enabled manually, so `Enabled on 1
Peer(s)` does not prove that Core is the enabled Client. The UI currently gives
the user no way to identify and disable every member of `extensions.enabled[]`
before changing the shared version or uninstalling the Extension.

This is a regression, not a new interaction model:

- Client commit `784ae12` rendered a Client selector at the top of the
  Extensions list, defaulted it to the current browser Client, and passed the
  selected Client ID to every Extension card;
- Registry integration commit `c488ebe` retained a selected-Peer variant;
- native Module Federation cutover commit `cae553f` removed the selector and
  reduced the page to the current browser Client;
- Client commit `784ae12` also rendered `ClientList` in Settings;
- commit `2b31ba9` removed that list while making environment configuration
  read-only. Current Client configuration was later restored, but all-Client
  management was not;
- `clientList.vue` and `clientCard.vue` still exist and are currently orphaned.

## Product Behavior

### Extensions page

Add one Client selector above the Extension list. It defaults to the current
browser Client and lists every row returned by `Client.list()`. Each option
shows the Client nickname and a short identity hint; the current browser Client
is explicitly identified.

For every card:

- switch state is `extension.enabled.includes(selectedClient.id)`;
- selecting another Client changes only the switch projection, not the shared
  Extension row or version controls;
- the total enabled count remains visible because version change and uninstall
  are deployment-wide operations and remain disabled until `enabled[]` is
  empty;
- a successful enable/disable response replaces the displayed Extension row,
  so the selector, count, version gate and uninstall gate stay coherent;
- a selector change never starts or stops a runtime by itself.

### Enable/disable dispatch

The page-level application coordinator owns topology dispatch:

1. When the selected Client is this browser Client, call the existing
   `WebExtensionHost.enable/disable`. This preserves Module Federation load,
   lifecycle compensation and the atomic database RPC.
2. When another selected Client has `rest_api_url`, call its generic Host API:
   `POST /extensions/{namespace}/{name}/enable|disable`, using the existing
   authenticated `Client.request` path and `InstalledExtensionSchema`.
3. When another selected Client has no management endpoint, update its durable
   desired enablement through the existing atomic
   `set_extension_peer_enabled` state-port operation. Do not call a runtime
   lifecycle that this browser does not own.

For an unaddressable Client, the switch therefore means desired state:

- enable is realized when that browser next starts or restores its Web Host;
- disable prevents its next restore, but an already-open remote browser may
  continue running until it reloads or closes because it has no management
  endpoint;
- the UI labels this limitation instead of claiming synchronous runtime
  control.

The database write still goes through the RPC rather than directly updating the
array. The database remains the concurrency authority and verifies that the
selected Client exists.

This coordinator belongs to `client-web`; `WebExtensionHost` remains the Host
SDK for this browser only and remains unaware of database tables or remote
Client topology. No new Core route, schema, RPC or Registry contract is needed.

### Setup entry is independent of the selected Client

The selected Client controls only the card switch. The setup wizard is a
whole-Extension experience contributed by the running Web Distribution, so its
availability remains:

`getExtensionHost().getSetupContribution(extension.name) != null`

It must not be derived from the selected Client's enabled flag. Consequently,
selecting Core can show and control Core enablement without hiding a setup
entry already supplied by the current Web runtime.

### Settings page

Restore the existing all-Client list below two clearly separated scopes:

1. this browser's bootstrap and Client configuration;
2. all registered Clients in the connected deployment.

The all-Client section lists, refreshes, health-checks and edits Client name,
REST API URL and declared configuration through the existing Client model. It
does not add manual Client creation or deletion: Clients register themselves,
and this follow-up restores management of existing records rather than
introducing a second registration lifecycle.

## Source Change Map

Client PR #68 branch only:

- `apps/client-web/src/views/extensions/extensions.vue` and
  `extensions.scss`: load Clients, own selected Client, render selector and pass
  selected/current identities to cards;
- a small `client-web` application coordinator near the Extensions view:
  dispatch current-Web runtime operations, remote-Host operations, or remote-Web
  desired-state operations without expanding `WebExtensionHost`;
- retain one initialized `ExtensionStatePort` behind the application
  integration seam so the coordinator can invoke the existing atomic RPC for a
  remote Client; do not expose SQL or PostgREST details to cards;
- `apps/client-web/src/components/extension/extensionCard/*`: separate
  selected-Client switch state from current-Web setup contribution, expose
  mutation availability/reason, and consume returned rows;
- `apps/client-web/src/views/settings/settings.vue` and `settings.scss`: restore
  `ClientList` under an explicit all-Client section;
- existing `clientList/*` and `clientCard/*`: only focused correctness and UX
  repairs needed by restored use;
- English and Simplified Chinese messages for selector identity, unavailable
  management endpoint and Settings section labels;
- focused unit/view tests. Generated database files remain untouched.

Core PR #52, Registry source and database schema are out of scope.

## Verification Plan

Focused tests must prove:

1. selector defaults to the current browser Client and projects `enabled[]` for
   the selected Client;
2. selecting the current browser Client dispatches through
   `WebExtensionHost.enable/disable`;
3. selecting an addressable remote Client calls the exact generic Core Host
   route and applies the returned Extension row;
4. an unaddressable remote Client uses only the atomic state-port RPC,
   performs no local lifecycle call, and reports desired-state semantics;
5. selecting Core does not hide the current Web setup contribution;
6. version and uninstall guards continue to use the complete `enabled[]`;
7. Settings renders and refreshes the all-Client list and edits Client metadata
   and configuration without conflating it with this browser's bootstrap form.

Repository gates after the coherent edit batch:

- focused Vitest suites for the view, card, coordinator and Client list;
- `pnpm --filter @inkcre/client-web type-check`;
- `pnpm check`;
- `git diff --check`.

No live preview, merge, Registry publication or database mutation is implied by
source implementation.

## Implementation Result

- The Extensions page now defaults a Client selector to this browser, displays
  every registered Client and projects each card switch from the selected
  Client's membership in `enabled[]`.
- The application coordinator dispatches current-browser lifecycle, remote Host
  API, or unreachable-Client desired-state RPC operations and verifies that the
  returned row changed the selected Client.
- Failure to load the wider Client list now degrades to current-browser-only
  management instead of hiding the Extension management surface.
- Setup contribution availability is independent of selector state; disabling
  another Client does not close or stop this browser's setup/runtime.
- Settings now separates this browser's bootstrap/configuration from all
  deployment Clients. The restored list handles load failure and health-check
  completion; Client metadata uses an explicit validated update action rather
  than the former nonexistent inline `confirm` event or an upsert lifecycle.
- No Core, Registry, generated database contract or delivery automation changed.

Verification:

- focused follow-up suites: 6 files, 17 tests passed after final review fixes;
- `pnpm --filter @inkcre/client-web type-check`: passed;
- `pnpm check`: passed with 27 files / 110 tests plus every workspace build and
  package contract;
- `pnpm type-check:ts7`: passed;
- `pnpm lint:type-aware` still reports only pre-existing diagnostics in unchanged
  generated/core/runtime files; none is in this follow-up's source;
- `git diff --check`: passed.
