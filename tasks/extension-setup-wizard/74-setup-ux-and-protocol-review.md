# Setup UX and Protocol Review

## Why This Review Exists

Black-box acceptance of Twitter `0.2.0` reached the Bookmark Source step and
exposed a connected group of defects rather than isolated presentation polish:

- the step says **Choose a Bookmark Source**, but when no Source exists it
  silently replaces selection with a nickname text field;
- the schedule editor exposes unexplained `Daily hour` and `Minute` numbers;
- the wizard uses raw `select`/`input` elements and hard-coded colours instead
  of the application's UI package and theme tokens;
- button loading indicators do not work because `InkButton` owns `isLoading`,
  while the implementation passes an unknown `loading` prop;
- setup Source/Cron/Job work is routed through the Twitter Core Distribution
  even though these are ordinary shared-database domains already available to
  the Web Peer;
- the accepted semantic HTTP design was replaced during Peer reconstruction by
  one `POST /twitter/setup` endpoint with a seven-way `action` discriminator.

The final point is implementation drift. HLD 3 specified semantic routes. The
Peer-native implementation compressed them into an action dispatcher without
recording or reviewing that change.

## Corrected Authority Boundary

### Twitter Core Distribution

The Core Distribution keeps only work that requires Twitter's private durable
state, provider interaction, or callback ingress:

- coherent OAuth App config replacement and account reset;
- begin and observe OAuth authorization transactions;
- callback code exchange, current-user lookup and token persistence;
- disconnect account;
- a Web-safe OAuth/account projection.

It does not list, create or select Sources; create or edit Crons; create Jobs;
or store selected Source/Cron IDs in Extension state.

### Twitter Web Distribution

The Web Distribution owns setup orchestration and uses ordinary Web Peer APIs
for the ordinary deployment resources:

- list and create `extensions.twitter.bookmark.Source` rows;
- list, create and update the selected Source's ordinary collection Cron;
- enable the Cron and create the initial ordinary collection Job on Finish;
- derive setup readiness from OAuth status plus current Source/Cron facts.

This is direct use of existing InKCre authorities, not a second Source/Cron
implementation. Normal duplicate submission is prevented by pending UI state.
Rare duplicate Sources or Jobs remain acceptable for this single-user product.

### Twitter Extension state

State retains only Extension-produced OAuth/account facts. The rejected
`bookmark_source_id` and `bookmark_cron_id` copies are removed. Closing and
reopening the wizard rediscovers Source/Cron truth from their own relations.
When exactly one eligible Source exists it may be preselected; multiple Sources
require an explicit visible choice.

The current `authorization_id` in bookmark Job parameters exists only to reject
a low-probability reconnect/old-job race. It forces generic Source/Cron creation
back through the private Core Extension state. The correction removes it from
the Web-facing collect config. At execution time the Source reads the current
Twitter account from Extension state. This deliberately trades that rare race
guard for a substantially simpler and more truthful domain boundary.

## Peer-native OAuth API

Peer HTTP v1 advertises one fixed method and URL per capability. Rather than
expanding that generic protocol with caller-selected paths, Twitter advertises
a small set of fixed semantic operations:

| Capability | HTTP operation | Request body |
| --- | --- | --- |
| `inkcre.twitter.setup.status.v1` | `GET /twitter/setup` | none |
| `inkcre.twitter.oauth-app.configure.v1` | `PUT /twitter/setup/oauth-app` | OAuth App fields and reset confirmation |
| `inkcre.twitter.oauth.begin.v1` | `POST /twitter/setup/oauth-transactions` | none |
| `inkcre.twitter.oauth.transaction.read.v1` | `POST /twitter/setup/oauth-transaction` | `{transaction_id}` |
| `inkcre.twitter.oauth.disconnect.v1` | `DELETE /twitter/setup/account` | none |

The fixed POST for transaction observation is the one bounded adaptation from
the earlier dynamic GET route. It avoids adding variable paths to the generic
Peer transport. Each request has one schema and one meaning; there is no
`action` field or internal dispatcher. Discovery of the status capability is
the setup-availability signal. The remaining capabilities are advertised by the
same running Twitter publication and invoked only by the Twitter Web target.

Cross-target coupling does not disappear: the two Twitter Distributions still
share an Extension-owned protocol. The correction removes accidental coupling
to Source/Cron/Job implementation and prevents one endpoint from becoming an
unversioned command bus.

## Corrected Bookmark Source Experience

Step 3 becomes **Set up bookmark collection** and has two explicit sections.

### Source

- If eligible Sources exist, show an `InkDropdown` labelled **Bookmark Source**
  with an explicit **Create a new Source** choice/action.
- If none exist, show a clear empty state: **No Bookmark Sources yet**, explain
  that setup can create one, and offer **Create Bookmark Source**.
- Creation reveals a separately titled **New Bookmark Source** form with a
  short description and an `InkInput` for nickname. It is never presented as a
  selection field.
- Selecting an existing Source does not rename it.

### Collection schedule

- Show the section only after a Source is selected or created.
- Use the established `InkPicker` time happy path rather than separate numeric
  hour/minute inputs.
- Label it **Collect bookmarks daily at** and state that execution uses the Core
  deployment timezone. If `core.cron` configuration is readable, show the exact
  IANA timezone; otherwise say **Core deployment timezone**, not an invented
  local-browser time.
- Reuse/update the selected Source's ordinary collection Cron when one exists;
  otherwise create one disabled. Finish enables it and runs one initial Job.

## Wizard-wide UX Correction

- Use `InkButton :is-loading` and one explicit pending operation identifier;
  disable conflicting navigation/actions while that operation runs.
- Show authorization polling as its own waiting state rather than an idle link
  plus text.
- Keep Twitter's always-available Close action. Closing aborts browser work and
  does not mutate durable setup facts.
- Add Back/Continue semantics for locally visited steps while still deriving
  resumability from durable facts on mount.
- Replace raw form controls with `InkDropdown`, `InkInput`, `InkPicker`, and
  normal `InkButton` happy paths.
- Keep the stepper inside Twitter, but use application theme tokens and quiet
  progress styling instead of hard-coded blue/grey circles. Do not introduce a
  generic Host wizard framework or a new UI dependency.
- Add concise titles and descriptions to OAuth App, account authorization,
  Source, schedule and Finish sections. English Extension-owned copy remains
  acceptable for this slice.

## Version and Delivery Consequences

Published Distribution bytes are immutable, so this correction is not a
replacement of `inkcre/twitter@0.2.0`:

- Twitter Python Distribution becomes `0.2.1`;
- Twitter Module Federation Distribution becomes `0.2.1`;
- `@inkcre/core` Web package becomes `0.1.2` if the ordinary Cron update method
  is added there; the MF association then requires `@inkcre/core >=0.1.2 <0.2.0`;
- Core Host SDK itself needs no new generic API or version for this correction.

Publication, preview delivery, installed-version change and remote mutation
remain separately authorized actions.

## Implementation Batches

### Batch A — Core Twitter protocol contraction

1. Remove Source/Cron/Job DTOs, setup state fields, action union and dispatcher
   from the Twitter package.
2. Publish the five semantic fixed Peer HTTP inbounds and routes above.
3. Keep callback/config/account/transaction behavior and safe provider errors.
4. Remove `authorization_id` from bookmark collect config and resolve the
   current account at operation start.
5. Advance the Python Distribution to `0.2.1` and update focused route,
   capability, state and bookmark collection tests.

No new generic Core business API, database migration, lock, transaction helper,
Source cleanup or Job deduplication is introduced.

### Batch B — Web domain composition and UX

1. Replace the action client with methods targeting the fixed semantic
   capabilities.
2. Compose Sources, Crons and the initial Job through existing `@inkcre/core`
   Web Peer models; add only the missing ordinary Cron update method.
3. Rework Step 3 into explicit select-versus-create and schedule sections.
4. Correct every loading binding and operation interlock.
5. Restyle the Twitter-owned progress/navigation and replace raw controls with
   `@inkcre/ui-web` happy paths.
6. Advance Web package/Distribution versions and native MF metadata.

### Batch C — Verification and review handoff

- Core focused OAuth/capability/bookmark tests, six-wheel verification and full
  pinned `pdm run check`;
- Web setup API/domain tests, behavioral Vue tests for empty/existing Source,
  pending actions, resume and Finish, then full `pnpm check` and native MF
  closure;
- no strict HTML/CSS snapshot validation and no new Close-button regression
  test;
- update the task packet with exact evidence, then stop at PR ready for review
  unless later remote actions are explicitly authorized.

## Review Gate

This document is a proposed correction produced from black-box evidence. It
does not authorize source edits. Before implementation, confirm that the
corrected authority split, five fixed capabilities, removal of
`authorization_id`, and `0.2.1` immutable Release are accepted together.
