# Core Python Extension Host Runtime

This document owns the expensive lifecycle contract of the independently released
`inkcre-extension-runtime-core-py` package. Core business capability semantics remain owned by the Core repository and the
shared Hub.

## Registration And Active Effects

```text
entry-point import -> process-monotonic capability type registration
Extension start    -> exact active routes + Peer inbounds + public claims
Extension stop     -> withdraw those exact active effects
package replacement -> process restart
```

Imported Source、Resolver and Sink classes remain registered for the lifetime of the interpreter. Disable does not restore
an earlier registry map or simulate Python module unload. This preserves decoder availability for persisted Blocks and avoids
pretending that `sys.modules` plus transitive imports can be rolled back safely.

One startup retains only the route objects and Peer inbound capability IDs it actually published, plus its exact public-route
claim. Stop and failed-start cleanup remove those identities without reconstructing a global before-state, so unrelated later
registrations are not overwritten. Source catalog persistence synchronizes the current monotonic registry explicitly after a
successful startup.

An imported exact Project version remains the process boundary. Install/upgrade may replace a Distribution only when no Peer
is enabled, but a process that imported the previous Project must restart before executing the replacement. Re-enable of the
same loaded version uses ordinary entry-point loading and the retained Python modules; active routes and Peer inbounds are
published fresh.

## Module Ownership

`DistributionModules` uses standard entry-point loading and verifies that every loaded module in the canonical
`extensions.<name>` package resolves to a file owned by the acquired Distribution. It does not delete, restore or shadow
`sys.modules`, and it does not create a second import cache.
