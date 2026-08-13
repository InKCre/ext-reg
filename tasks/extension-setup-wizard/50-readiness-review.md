# Implementation Readiness Review

## Evidence Closed

- Current upstream `origin/main` for ext-reg, Core, Client and organization
  workflow policy was inspected from clean snapshots, not inferred from older
  task branches.
- Product authority, config/state/Source boundaries, callback topology, Web/Core
  Host SDK boundaries and delivery stop condition are accepted.
- Core database schema, role/trigger model, lifecycle publication, middleware,
  Extension consumer, Source/job APIs and current Twitter implementation were
  traced to concrete symbols.
- Client Host lifecycle, installed state port, `Client` peer discovery, card,
  `InkDialog`, Twitter MF entry, native artifact checks and delivery workflows
  were traced to concrete symbols.
- X OAuth requirements and Authlib's supported async PKCE/refresh path were
  checked against primary documentation.
- An isolated Authlib `1.7.2`/HTTPX probe proved S256, authorization-code token
  exchange, `client_secret_basic`, automatic refresh and `update_token`.
- A temporary PDM `2.27.0` resolution proved Authlib/HTTPX fit the existing Core
  dependency graph without changing the real repository.
- The absence of local Docker was checked. The existing SSH Docker provider,
  target alias and cross-repository contract-sync path were verified as the
  planned exact-image mechanism.
- Existing first-party wheel and MF CD paths already support the same
  `inkcre/twitter@0.2.0` Release; ext-reg requires no source change.
- A read-only production Registry probe confirmed `0.1.1` is the current
  two-association Twitter Release and `0.2.0` is unused, so the immutable
  version plan has no collision.
- Organization `CONTRIBUTING.md` and `GOVERNANCE.md` were re-read: the plan uses
  latest-main focused branches, PR-only changes, repository checks, explicit
  dependency/evidence/risk/rollback notes, and protected-main-only publication.

## Independent Plan Review — 2026-08-13

The first closed draft was challenged against multi-Core execution, one-use
OAuth codes, Source cardinality, generic logging and cross-repository admission.
It was not accepted unchanged. The review found and corrected twelve material
problems:

1. **Stale config/runtime cache across Core Peers.** State reads were fresh, but
   `ExtensionBase.config` and `TwitterAPI.SINGLETON` were still process-local
   snapshots. The corrected plan adds authoritative `get_config()` reads for
   setup/provider operations, uses a fresh closed Authlib client for each
   official provider operation, and limits the retained Twikit cache to matching
   fresh config.
2. **False OAuth crash recovery.** An exchange lease could not determine whether
   X had consumed the one-use authorization code. The corrected state machine
   has one `pending -> exchanging` claim and no reclaim; a crash leaves that
   transaction to expire while the user starts a new one.
3. **Accidental Source uniqueness.** `ensure_one` implied one Source per type,
   which the Source product does not guarantee. The corrected Source authority
   only ensures that at least one initial Source exists and preserves multiple
   existing Sources.
4. **Review evidence mistaken for upstream admission.** An exact unmerged Core
   image is valid for Client review, but not final merge authority. The Client PR
   is now explicitly merge-blocked until Core lands and its generated contract
   is refreshed against the admitted revision.
5. **Overlapping OAuth flows could reorder user intent.** A late older callback
   could otherwise overwrite a newer authorization. Begin now supersedes prior
   non-terminal flows and every callback commit rechecks the transaction state.
6. **Old collection evidence could produce false readiness.** A finished job
   from a previous account could otherwise make a reconnect immediately ready.
   A timestamp alone still races between provider validation and job creation.
   Account state now carries an opaque `authorization_id`; Finish jobs and
   readiness must match it, and a raced job fails before provider work.
7. **Teardown could roll config backward.** Base `on_close()` currently persists
   its local config snapshot. A stale Core Peer could therefore overwrite a
   newer OAuth App committed elsewhere merely by disabling. The plan moves
   config persistence to explicit command time and makes base teardown read-only
   with respect to config.
8. **State compatibility was not actually preflightable.** The draft promised
   that an incoming Distribution would validate existing state before a version
   change, but no migration metadata exists and loading future bytes would mutate
   the active interpreter. The MVP now permits version change only for empty
   state and rejects non-empty state before mutation.
9. **The planned polling cancellation API did not exist.** Current
   `Client.request()` has no `AbortSignal`, so the wizard would otherwise fork
   authentication and retry logic. The corrected plan extends that existing
   deep client path and tests signal propagation through its 401 retry.
10. **The existing 401 retry drops JSON headers.** A refreshed OAuth-App PUT
    could otherwise replay its body without `Content-Type`. The same Client
    correction now preserves every non-auth request field and replaces only the
    Authorization header.
11. **FastAPI blockers were hidden by the Client error parser.** Core uses a
    bounded string `detail`, while Client only recognized `message`/`error`.
    The corrected deep client path accepts string `detail` but does not stringify
    structured validation input.
12. **The Client PR could not honestly be green before Core admission.** Its
    GitHub checks deliberately resolve protected stable Core, not a feature
    image. The corrected handoff keeps Core green, opens Client Draft/reviewable
    with exact local evidence, leaves the stable check as an explicit dependency
    gate and adds no CI bypass.

The review also removed raw query values from generic logging, required Twitter
to bound provider exceptions before generic/Source-job logging, and made
public-route claim ordering/rollback explicit. It deliberately did not redesign
Core-wide exception observability. No new framework, service, table, callback
broker or cross-process invalidation channel was added.

## Design Review Against Common Failure Modes

### No hidden generic framework

There is no generic setup engine, OAuth broker, transaction service, second
state table, capability matcher, Source ownership layer or notification system.
The only generic APIs are the two proven reusable needs: typed Extension state
and one optional Web setup contribution. OAuth and wizard semantics remain
Twitter-owned.

### No authority inversion

Core/PostgreSQL owns Extension-state transactions. Source concurrency remains
in the Source domain. Extension code receives typed operations, not database
objects. Web uses semantic Twitter commands and never interprets raw state.

### No browser-origin coupling

The provider calls a Core-owned exact callback. Web observes an ordinary
authenticated transaction endpoint. No opener, `postMessage`, redirect URI or
JWT binds Core to the Web origin.

### No compatibility ambiguity

Core and Web Host SDKs advance to `0.1.1`; Twitter advances both native
Distributions to `0.2.0` and requires the new Host versions before bytes are
loaded. Existing Extensions remain compatible.

### No generated-contract shortcut

Client generated types come from an exact unmerged Core branch image on the
configured SSH Docker daemon. They are not hand-edited and do not require an
early merge.

### No delivery-scope expansion

Two source PRs are sufficient. ext-reg source, publisher workflows, deployment
and black-box acceptance remain unchanged/out of scope.

## Residual Risks With Chosen Behavior

These are implementation risks with specified handling, not unanswered design
questions:

- X may revoke/rotate credentials: preserve durable account facts and project
  `reconnect_required`; never silently clear Sources.
- Two processes may attempt provider refresh: Core serializes state commits and
  conditional writes reject stale token replacement; a transient loser fails
  without erasing a newer account.
- A Core may die after claiming a callback exchange: the one-use code is not
  reclaimed; that transaction expires and the user starts a new one while an
  existing account remains.
- Registry/Core may be unavailable: wizard reports operational unavailability
  and leaves durable config/state/Sources unchanged.
- First collection may fail: Finish returns the accepted job; an explicit retry
  may create a new job only after the prior one is failed.
- English-only first-slice copy is accepted as a presentation limitation rather
  than introducing a cross-Remote localization contract.
- The trusted generic PostgREST/config API can still bypass Twitter's semantic
  OAuth-App command. That existing operator boundary is intentionally retained;
  the Twitter projection reports incompatible direct edits as invalid without
  silently deleting the prior account. Tightening all Extension config writes
  is a separate product contract.

## Exit Assessment

Product design, corrected HLD, repository/file plan, version plan, dependency
feasibility, exact contract generation path, focused verification and PR
handoff are all specified. The independent review found concrete defects and
the packet now incorporates their resolutions. There is no unfinished
investigation, exploratory branch, spike or schema/API choice required before
source implementation.

The remaining gates are procedural only:

1. Sir reviews this implementation proposal.
2. Sir gives the separate explicit start required before source mutation.
3. Commit/push/PR operations remain separately unauthorized until explicitly
   requested.
