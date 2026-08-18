# Setup and Host SDK Boundary Proposal

## Accepted Product Boundary

There is no language-neutral or Host-owned Setup Wizard API. Setup is an
Extension product concern assembled from two Peer-specific Extension APIs and a
Twitter-specific cross-target protocol.

## Web Host SDK

The generic Web contribution remains deliberately small:

```ts
interface WebExtensionModule {
  setup?: {
    component: VueComponent
  }
}
```

`client-web` detects the contribution on the already loaded Extension, shows the
card action, owns the popup shell, mounts the component and lets it request that
the shell close. It does not own steps, progress, readiness, OAuth, Core Peer
selection or Source commands.

The setup component may use the ordinary `@inkcre/core` Web Peer APIs available
to an Extension. The Host SDK does not proxy every Core contribution through a
new setup context.

## Core Host SDK

Core's generic addition is deployment-wide Extension state, not a setup engine:

```python
class ExtensionBase[Config, State](
  config_cls=...,
  state_cls=...,
):
  ...
```

The Host SDK gives Extension code typed config/state access without exposing the
SQL model. State mutations are delegated to Core's shared state authority; the
SDK does not guarantee concurrency. Existing lifecycle, route, Source and direct
Peer-internal contribution patterns remain Peer-specific Core Extension API.

The Core Host SDK does not define OAuth providers, transactions, setup steps,
readiness blockers, bookmark Sources or a generic setup projection.

## Twitter-owned Cross-target Protocol

The Twitter Web and Core Distributions jointly own:

- the setup projection;
- OAuth App validation and account authorization commands;
- authorization transaction polling;
- the standalone callback/result page;
- bookmark Source selection/creation;
- readiness and Finish/start semantics.

This protocol uses the existing authenticated Web-to-Core Extension route and
Peer discovery/delegation facilities. It is not promoted to `client-web`, Core,
the Registry, or a generic OAuth/setup framework merely because two Twitter
Distributions consume it.

## Resulting Topology

```text
client-web card/popup shell
  -> Twitter Web setup component
    -> ordinary Web Peer/Core access facilities
      -> Twitter Core setup API
        -> Core config/state authorities + Source domain + X OAuth
```

Each layer owns one existing concern. The only new generic Host SDK surfaces are
the optional Web setup component and typed Core Extension state access.
