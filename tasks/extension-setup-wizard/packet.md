# Extension Setup Wizard — Task Dashboard

## Objective

Deliver the deployment-wide Extension setup experience, with `inkcre/twitter`
as the first vertical slice, while keeping Registry Release truth, deployment
installation, Peer enablement, native Distribution presence, runtime activity,
Extension config/state and Source/Cron/Job ownership distinct.

## Current State

- Product setup behavior and the Twitter wizard are implemented in Core PR #65
  and Client PR #71 and have reached the setup popup in preview.
- Preview delivery controllers and the multi-Extension static Registry builder
  have landed through their own completed batches.
- Re-enable acceptance exposed the next architectural defect: Core asks the
  Registry before discovering an exact wheel already present in its current
  interpreter.
- D041–D043 freeze the correction: `ext-reg` owns a per-Peer-type Extension
  Host Runtime family; Python activation is local-first; `ExtensionManager` and
  `ExtensionBase` belong to that Runtime; Core's rich `ExtensionModel` remains
  the database authority; no Repository or generic Port layer is introduced.
- Local source implementation and Peer adoption checks are complete. Commit,
  push, package publication, released-lock normalization and remote deployment
  remain separately gated.

## Current Authority

Read these files in order; they are the only active control surface:

1. [State and authorization](active/00-state.md)
2. [Final review findings](active/10-review/runtime-alignment-findings.md)
3. [Adjacent implementation batches](active/20-batches/runtime-alignment.md)
4. [Impact Handshake](active/30-handshake/runtime-alignment.md)
5. [Implementation plan](active/40-plan/runtime-alignment.md)
6. [Implementation result](active/50-implementation/runtime-alignment.md)
7. [Acceptance result](active/60-acceptance/runtime-alignment.md)

The previous chronological files remain evidence, not current implementation
authority. Their status and replacement are recorded in
[History index](history-index.md).

## Frozen Decisions

- An `extensions` row means the Release is installed in the deployment.
- `enabled[]` is per-Peer durable intent. `present` and `running` are derived
  runtime observations and are not stored in the deployment database.
- Python exact local presence is checked before Registry configuration or I/O.
  A local miss may use the configured Registry and standard Python packaging.
- Python and Web have separate Runtime packages and native lifecycle models.
  They share Release/Distribution contracts, not one universal lifecycle.
- Host SDK is the Extension-facing surface of the same per-Peer Runtime/Peer
  implementation, not another package or release unit.
- Core owns the `extensions` schema, migrations, transactions and rich
  `ExtensionModel` Active Record. The Core Runtime directly consumes that model
  and the concrete FastAPI/Source/Resolver/Peer APIs.
- Client retains its rich Extension model, Peer delegation, application UI and
  popup shell. Its Runtime directly consumes the concrete Module Federation
  Host and Client Extension APIs.
- Do not add `ExtensionRepository`, `SQLExtensionStore`, generic Persistence or
  Contribution Ports, a database `present` field, peer bindings, generic target
  matching or a shared Python/Web lifecycle state machine.
- Registry Pydantic/FastAPI models generate the checked OpenAPI/JSON Schema.
  Mature generators produce Python bindings and Web fetch/Zod bindings; CI
  regeneration plus a clean diff is the drift gate.
- Python development uses one root PDM workspace and `pdm.lock`; no uv command,
  uv lock or nested Python environment is a repository interface.
- Repositories do not maintain automated test suites. Validation is limited to
  generated-contract checks, static analysis, package builds and deployment
  smoke where applicable.
- Preview delivery must not use full-tree public reads, byte comparisons,
  cache-busters, digest substitutions, long propagation retries or similar
  low-ROI consistency machinery.

## Review/Implementation Loop

Future work is processed as adjacent issue batches rather than appended as a
new chronological design essay:

1. record evidence and diagnosis in `active/10-review/`;
2. group adjacent findings in `active/20-batches/`;
3. freeze the affected invariants and authority in `active/30-handshake/`;
4. revise the one active plan in `active/40-plan/`;
5. review that plan before asking for source authorization;
6. after authorization, record implementation evidence in `active/50-implementation/`;
7. record black-box acceptance and remaining findings in `active/60-acceptance/`.

Implementation batches do not automatically authorize the next batch. Commit,
push, package publication, cross-repository mutation, preview deployment and
merge remain separate authorization boundaries.

## Current Gate

Toolkit 0.2.0 and both Runtime 0.1.0 release units are locally green. The next
gate is explicit authorization to commit/push and publish those independent
packages; only after publication can Core and Client record normal released
dependencies and frozen locks. Remote preview acceptance remains later.
