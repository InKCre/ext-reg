# HLD 4 — Web Host Contribution and Wizard UI

## Web Host SDK Contract

`@inkcre/core` adds one optional contribution to the existing Module Federation
module:

```ts
import type { Component } from 'vue'

export interface ExtensionSetupContribution {
  component: Component
}

export interface ExtensionModule {
  initialize?(): Promise<void>
  activate?(): Promise<void>
  deactivate?(): Promise<void>
  dispose?(): Promise<void>
  setup?: ExtensionSetupContribution
}
```

`WebExtensionHost.getSetupContribution(name)` returns the contribution only
while that exact Extension is running in the current Web Peer. It does not load
a disabled Remote merely to inspect setup. The running map stores the loaded
module beside its lifecycle object.

The Host owns no setup context, steps, state, Core client or database port. The
component uses the ordinary Web Peer APIs already available to Extensions.
The generated database row will contain the new `state` column, but
`InstalledExtensionSchema` continues to project only installation/config facts;
the PostgREST adapter neither interprets nor writes raw Extension state.

## Card and Popup Shell

The Extension card derives setup availability from two facts:

1. this Web Peer's UUID is present in the installed row's `enabled[]`;
2. the running module contributes `setup`.

When both hold, the card shows **Setup**. When the Extension is disabled here,
the card explains that local enablement is required. The existing trusted
**Edit config** operation remains an expert surface; the wizard is the guided
product path but does not invent a new authorization boundary around config.

An enabled row with no running module is not mislabeled as merely disabled: the
card uses the Host's existing runtime-error projection to report that setup is
unavailable. A running Extension with no setup contribution simply has no Setup
action. Twitter `0.2.0` is expected to contribute one; failure to do so is a
runtime/package defect, not a hidden fallback to Host-owned UI.

The shell uses the existing `InkDialog` happy path:

```text
showCancel=false
showConfirm=false
closeOnScrim=false
default slot = dynamic setup component
component close event -> dialog closes
```

The Twitter component owns Back/Next/Cancel/Finish. If local disable or unload
occurs, the shell clears the mounted dynamic component and awaits one Vue tick
before asking the Host to stop/dispose the Remote. Dialog animation is not the
lifecycle boundary. No generic stepper component or setup engine is introduced.

## Core Endpoint Discovery

The Twitter Web Distribution discovers command endpoints through the existing
`Client` model:

1. call `Client.list()`;
2. keep clients with a `rest_api_url`;
3. probe authenticated `GET /extensions/inkcre/twitter` on each;
4. report reachable candidates and whether the shared installed row contains
   that client UUID in `enabled[]`;
5. if none is enabled, require the user to select a candidate and explicitly
   call `POST /extensions/inkcre/twitter/enable`;
6. use the selected enabled endpoint for `/twitter/setup` and setup commands.

The UI does not guess from a client name or label. A Core endpoint is merely the
transport for deployment-wide config/state/Source authorities. If multiple
enabled endpoints are reachable, the user may choose one; the selection is
ephemeral and is not persisted as Extension ownership.

## Twitter Component

The Twitter Remote exports the normal lifecycle plus
`setup.component = TwitterSetupWizard`. The component owns the four steps:

```text
Prepare -> Connect account -> Bookmark Source -> Review and start
```

On mount and after every successful command it reloads the setup projection and
derives the first unsatisfied step. Local `currentStep` only controls navigation
inside that mounted popup and is never a durable completion authority.
When multiple existing bookmark Sources are eligible, the component defaults to
the oldest stable Source ID and lets the user select another for Finish; this
selection is local because any eligible Source satisfies the whole-Extension
baseline.

The component uses established dependencies only:

- `@inkcre/core` `Client` for authenticated Core calls;
- existing `@inkcre/ui-web` form, input, dropdown and button components;
- a small accessible ordered-list step indicator styled inside Twitter;
- normal Vue state/composables; no form or state-machine framework is added.

The existing `Client.request()` happy path gains one optional
`signal: AbortSignal`; it forwards that signal through the original request and
the existing one-time 401 refresh retry. That retry preserves the original
method, URL/query, body, signal and non-auth headers such as JSON
`Content-Type`, replacing only Authorization. Twitter does not fork
authentication, error parsing or `fetch` into a second HTTP client merely to
support polling and probe cancellation.

The same parser recognizes a string FastAPI `detail` as the bounded API error
message, alongside its existing `message`/`error` cases. It never renders an
object/validation payload as text. This lets explicit Core enable/setup blockers
reach the wizard instead of collapsing to a generic HTTP status.

The first slice may ship English copy owned by the Twitter Distribution rather
than adding a cross-Remote i18n protocol. Localization is presentation follow-up,
not a hidden setup authority.

## OAuth Browser Flow

After Begin returns, the component renders a deliberate **Open X** link with
`target="_blank" rel="noopener noreferrer"`. It does not depend on retaining an
opener. While mounted, it polls the opaque transaction every two seconds until
terminal/expired. Timers and requests use one `AbortController` and are stopped
on cancel, unmount or transaction replacement.

Success reloads `/twitter/setup`; failure leaves a retry action and any previous
working account intact. Closing the dialog does not cancel the Core callback.
Reopening resumes from deployment facts, not the lost component instance.

## Web Version and Tests

`@inkcre/core` advances from `0.1.0` to `0.1.1`; existing Web Extensions remain
compatible, while Twitter `0.2.0` declares
`@inkcre/core >=0.1.1 <0.2.0`. The MF shared range follows that package version.

Focused tests cover Host contribution availability/cleanup; card gating and
dialog ownership; Core discovery and explicit enable;
four-step resume; credential submission redaction; polling cleanup/retry;
Source selection/Finish; `Client.request` abort propagation; PostgREST omission
of `state`; 401 JSON-request preservation; and error preservation.
Existing native MF closure
checks must still prove `mf-manifest.json`, the Remote entry and all assets.
