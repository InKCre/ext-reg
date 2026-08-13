# Product-design Working Model

## Proposed Product Concept

An **Extension Setup** is a resumable, Extension-specific user journey that
turns an already installed and enabled Extension Release into the Extension's
declared minimum usable state across the deployment. It is whole-Extension
setup, not setup of one individual feature or one Peer. It is not a Registry
lifecycle state and is not a synonym for installed, enabled, or running.

A **Setup Wizard** is the accepted presentation of that journey in
`client-web`: an action on an Extension card opens a popup whose content is an
Extension-owned multi-step installer. The setup entry requires at least that
this Web Peer has enabled and loaded the Extension; Core Peer enablement is a
separate prerequisite that the wizard may observe or guide. The durable product
contract is still the whole-Extension outcome and observable progress, rather
than the popup's currently displayed step number.

## Accepted Twitter Completion Direction

Twitter setup is complete when the whole Extension has reached its declared
minimum usable state. For the current Twitter Extension, bookmark collection is
the first concrete proof of that baseline rather than a separately scoped
feature wizard. At minimum all of the following are true:

1. `inkcre/twitter` is installed at one exact deployment version.
2. A selected compatible Core Peer is enabled for that Extension and exposes
   the Twitter setup operations.
3. The Twitter application configuration required by the selected backend is
   valid.
4. A Twitter account authorization is durable and can be restored by that Core
   runtime after restart.
5. Every resource declared necessary for the Twitter Extension's initial useful
   operation exists; in the first vertical slice this includes at least one
   eligible Twitter bookmark Source.
6. A bounded Extension-level readiness check confirms the authenticated account
   and required initial resources can begin useful work; it does not need to
   wait for a full historical sync.

The Web Peer is enabled to render the setup experience, but that is only a means
of presentation. The resulting setup facts are deployment-wide rather than
owned by that Web Peer.

## Product Principles Derived from the Proposal

- Display progress from observed domain facts rather than one manually toggled
  `setup_complete` boolean.
- Resume at the first unsatisfied prerequisite after reload, reconnect, or
  partial failure.
- A user may leave the wizard and return without losing successful steps.
- Setup may use one reachable Core Peer as a command/OAuth endpoint, but that
  does not make setup or future Source execution Peer-specific.
- The wizard guides the user through registering an X developer App and entering
  its Client ID and Client Secret. Deployment-wide `extensions.config` is the
  accepted authority for these user-declared values. Deployment-wide
  `extensions.state` owns Extension-produced account credentials, identity and
  OAuth transactions. Both use InKCre's trusted authenticated-Peer security
  boundary.
- The Extension defines one minimum setup baseline. Optional capabilities added
  later may have their own configuration journeys without retroactively making
  the whole Extension "not set up".

## Accepted UI Ownership

The narrowest reusable split is:

- `client-web` owns the Extension-card entry and popup container, including
  opening, closing, focus containment and mounting/unmounting its content.
- The enabled Web Distribution owns everything inside that popup: stepper,
  Back/Next/Cancel/Finish controls, step sequence, content, field validation,
  loading and recoverable errors, Core-facing commands, observed completion
  facts, and the final Extension-level readiness projection.
- The Extension Host SDK owns the small contribution contract that connects
  those two sides. It does not know Twitter fields, OAuth endpoints, Sources, or
  database tables.

This avoids hard-coding Twitter setup into `client-web` and avoids a premature
generic wizard engine. Extensions may need materially different setup flows;
their own Host SDK-bound UI is the correct place to express those differences.
Only popup behavior remains consistent across Extensions.

The setup action is available once this Web Peer has successfully enabled and
loaded the Extension, because its Web Distribution contributes the popup
content. This is a minimum availability condition, not a claim that this Web
Peer performs the Extension's Core work. Installed-but-disabled cards should
explain that the Extension must first be enabled here instead of offering a
broken setup action.

## Accepted Minimum Web Extension API

The Web Host SDK adds one optional setup contribution to the already
loaded Web Extension module. Conceptually:

```ts
interface WebExtensionModule {
  initialize?(): Promise<void>
  activate?(): Promise<void>
  deactivate?(): Promise<void>
  dispose?(): Promise<void>

  setup?: {
    component: VueComponent
  }
}
```

The Host renders `setup.component` inside its popup. The component owns its
entire flow and emits only a request to close the containing popup. A successful
Finish may request close, but it does not pass a `setup_complete` value back to
the Host; reopening the component reconstructs progress from Core-visible
facts.

This API deliberately does not include `steps`, `currentStep`, validation,
progress persistence, OAuth, Core Peer selection, Source creation, or a generic
setup status. Those are Extension-owned semantics. HLD closes the exact Vue
type and `close` event in [Web Host Contribution and Wizard UI](34-hld-web-setup.md).

## HLD Closure

The formerly open implementation shapes are now closed in HLD:

- the Web contribution is one Vue `Component` plus a `close` event;
- Twitter owns its exact config/state/setup protocol and Authlib OAuth client;
- Core owns one exact public callback contribution and database state
  transactions;
- Finish explicitly creates or reuses the first bounded collection job;
- the first release does not expose a newest-versus-history choice.

See [Canonical Extension State](32-hld-extension-state.md),
[Twitter Setup and OAuth Protocol](33-hld-twitter-protocol.md), and
[Web Host Contribution and Wizard UI](34-hld-web-setup.md).
