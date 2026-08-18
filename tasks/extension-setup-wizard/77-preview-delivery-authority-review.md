# Preview Delivery Authority and Readiness Review

## Review Trigger

The previous plan assigned Client/Core checks responsibility for building and
uploading deployable SPA, Module Federation, wheel and static Preview Registry
outputs. A later `workflow_run` delivery would download those artifacts and
deploy them. Sir identified this as a prohibited InKCre `.github` pattern.

This review removes that handoff without changing the accepted product topology:
Client still hosts a same-origin MF facade; Core still receives a sibling static
Python facade on a dedicated Cloudflare Pages project.

## Governance Reading

The organization policy gives pull-request checks and preview delivery different
authorities:

- required checks validate a candidate and remain merge evidence;
- an isolated preview may be delivered only for an eligible pull request under
  a trusted controller, exact-head verification, preview-scoped credentials,
  deterministic short-lived resources, cleanup and concurrency;
- fork pull requests receive no preview or production credentials;
- canonical publication remains protected-main authority.

Therefore the preview workflow must own its build and deployment. Checks may
compile/build as validation and may upload diagnostic failure evidence, but the
preview must not consume those outputs.

## Corrected Workflow Topology

```text
Required checks
  -> validate candidate
  -> merge evidence only
  -> no deployable artifact handoff

Trusted PR preview controller
  -> verify same-repository PR + exact head
  -> checkout trusted controller and exact candidate separately
  -> install frozen pnpm/PDM environments
  -> build Peer + relevant Extension Distributions
  -> inkcre-ext preview build
  -> deploy directly to PR-scoped Pages resource
  -> report preview status

Trusted PR-close controller
  -> retire exact deterministic preview resources
```

## Controller Landing Order

GitHub evaluates `pull_request_target` from the target repository's default
branch. A candidate pull request cannot activate a new or changed trusted
controller merely by carrying that workflow in its own head commit.

Therefore Client PR #71 and Core PR #65 cannot self-bootstrap this preview
migration. The remote landing order is:

1. prepare one controller-only change from each repository's current
   `origin/main`;
2. review and merge those controller changes into the corresponding `main`;
3. rebase or merge `main` into the feature pull requests only where their
   candidate-owned manifests, inventories or scripts require it;
4. synchronize PR #71 and PR #65 so the now-trusted default-branch controllers
   build their exact current heads;
5. perform the cross-repository preview acceptance.

The controller bootstrap changes also seed repository-wide Preview Toolkit
manifests, locks, inventories and build helpers into `main`. Otherwise the new
default-branch controller would immediately require files absent from every
other candidate branch. Extension producer metadata and built Distribution
bytes remain candidate-owned exact-head inputs. PR #71 and PR #65 then update
from `main` before their previews exercise the new path.

The old chain is explicitly rejected:

```text
checks -> upload deployable outputs -> workflow_run -> download -> deploy
```

## Client Preview Sequence

1. Trigger the trusted preview controller for pull-request changes; do not use a
   `workflow_run` of `Client checks` as delivery input.
2. Admit only the repository's eligible PR head. Fork PRs receive no preview
   credentials; GitHub's organization/repository approval setting governs when
   untrusted contributors may run secret-free Actions.
3. Checkout controller code from the trusted workflow revision and candidate
   source from the exact PR head.
4. Install pnpm from `pnpm-lock.yaml` and the root PDM development-tool project
   from `pdm.lock`.
5. Build the Client SPA and every MF Distribution listed in the preview
   inventory in this workflow run.
6. Run `pdm run inkcre-ext preview build` with the deterministic Client PR Pages
   alias as `--public-origin`, writing the static Registry projection into the
   SPA deployment directory.
7. Reverify the PR head immediately before external delivery and deploy that
   directory directly. Provider acceptance is the delivery gate; consumer-path
   acceptance remains a separate black-box activity.
8. Keep the existing PR-close cleanup authority and deterministic branch name.

The expected Client origin remains
`https://preview-client-web-pr-<number>.<client-pages-project>.pages.dev`, derived
from its existing `preview/client-web/pr-<number>` branch convention.

## Core Preview Sequence

1. Extend the existing trusted `pull_request_target` preview lane rather than
   routing through Core checks.
2. From the exact candidate checkout, install the frozen PDM development group,
   build all first-party Extension wheels, and write one explicit Python
   inventory.
3. Run `pdm run inkcre-ext preview build` with the deterministic Core PR sibling
   Pages alias as `--public-origin`.
4. Reverify the PR head and deploy the static tree directly to the dedicated
   `inkcre-core-py-extension-registry-preview` Pages project.
5. Set `EXTENSION_REGISTRY_URL` on the deterministic Heroku preview app to the
   precomputed Pages alias before releasing/starting Core.
6. Continue the existing Heroku/PostgREST/database delivery and smoke path.
7. PR-close cleanup removes the exact Pages branch in addition to the existing
   Heroku and preview-database resources.

The Core repository owns a non-secret project variable such as
`CLOUDFLARE_EXTENSION_PREVIEW_PROJECT`, whose accepted value is
`inkcre-core-py-extension-registry-preview`. With branch `pr-<number>`, the
precomputed public origin is
`https://pr-<number>.inkcre-core-py-extension-registry-preview.pages.dev`.
Cloudflare account ID and the minimally scoped deploy token remain preview
environment credentials and are never exposed to fork workflows.

## Alias Decision

`inkcre-ext preview build` needs the public origin before Pages deployment so it
can materialize absolute Release/native URLs. A random Pages deployment URL is
not available yet and would create a build/deploy cycle.

Use a deterministic PR-scoped branch alias, known from the project and branch
name before build. It is both the Toolkit's embedded public origin and Core's
configured Registry origin. A random deployment URL, cache-buster, content
digest, or byte-for-byte public read is not a second delivery authority.

Use simple branch names such as `pr-<number>` for the dedicated Core project.
Client may retain its current deterministic alias convention if the expected
hostname is derived once and asserted rather than guessed differently by the
Toolkit and workflow.

## Implementation Batches

### Batch A — Toolkit release unit

- move preview and publisher commands from the Registry service distribution to
  `inkcre-extension-toolkit 0.1.0`;
- keep one-way Registry-service dependency on Toolkit pure rules;
- remove the Registry service console entry point;
- run existing ext-reg checks; add no test.

Remote commit, push, merge and Toolkit publication remain separately authorized.

### Batch B — Peer package locks

- Client: add root PDM development-tool project and lock the released Toolkit;
- Core: add Toolkit to a dedicated development/tooling group and update its
  existing PDM lock;
- neither production/default runtime dependency set includes Toolkit.

### Batch C — Client preview migration

- delete the Twitter-specific Registry assembler;
- remove deployable SPA/MF/Release uploads from `Client checks`;
- replace `workflow_run` artifact delivery with the corrected exact-head preview
  controller;
- retain required checks independently and retain preview cleanup.

### Batch D — Core sibling facade

- build all first-party wheels and the facade inside Core preview delivery;
- deploy the dedicated Pages sibling before Heroku startup;
- pass the precomputed alias through `EXTENSION_REGISTRY_URL`;
- extend cleanup to the Core Pages preview branch.

### Batch E — Cross-repository preview acceptance

- land the Client/Core controller-only changes on their respective `main`
  branches before expecting either feature PR to use the new controller;
- confirm Client PR #71 and Core PR #65 checks remain green independently;
- confirm both preview workflows report success for their exact current heads;
- connect Client PR #71 preview to Core PR #65 preview;
- install and enable `inkcre/twitter@0.2.1`;
- confirm the Twitter Setup entry is visible and its popup opens;
- stop there; OAuth/provider black-box acceptance remains with Sir.

## Acceptance Criteria

The follow-up is complete only when all statements are true:

1. `inkcre-ext preview build` ships from the independent, PDM-consumable
   `inkcre-extension-toolkit` release and supports one explicit multi-Extension
   inventory containing Python and/or MF inputs.
2. Registry service and Toolkit share the same pure admission/projection code;
   Peer repositories contain no Release/path clone.
3. `Client checks` uploads no deployable SPA, MF or Release-preview output, and
   Core checks uploads no wheel or Preview Registry output for PR preview
   delivery. Repository checks may exercise builds and retain diagnostic
   failure evidence, but never retain a deployable preview handoff.
4. Client and Core preview workflows each build and deploy their own exact-head
   outputs in one trusted run; no deployable `workflow_run` artifact handoff
   remains.
5. Client preview serves its supplied MF facade on the Client Pages origin.
6. Core preview serves all supplied first-party Python wheels from its dedicated
   Pages sibling, and Core starts with that alias as fallback Registry
   origin.
7. Same-repository identity, exact-head reverification, preview environment,
   deterministic concurrency/resources, SHA-pinned Actions and PR-close cleanup
   remain intact. Fork PRs receive no preview credentials.
8. Existing repository checks pass; consumer black-box acceptance is recorded
   separately and this follow-up adds no test files or test cases.
9. Client PR #71 can open the `inkcre/twitter@0.2.1` setup popup while connected
   to Core PR #65 using only those PR-owned preview facades.

## Readiness Verdict

**Ready for implementation after this packet correction.**

No product or contract question remains. The implementation order is forced by
package availability: Toolkit split and release first, then locked Peer adoption,
then Client/Core workflow changes, then preview acceptance. The plan does not
require production Registry mutation or a per-PR Worker/D1/R2 deployment.

The prior local preview-builder source remains useful implementation evidence,
but it is in the wrong Registry distribution and must move before release. No
source mutation, commit, push, release, deployment or cross-repository change is
performed by this packet-only review.

## Preview Verification Restraint

Preview delivery optimizes for review availability, not artifact attestation.
The following are explicit anti-patterns for this task and must trigger a plan
review instead of another patch:

- downloading every public file and comparing it byte-for-byte with local build
  output;
- increasing retry counts or propagation windows to make an eventually visible
  preview look transactional;
- adding cache-busters or cache-control workarounds to force a delivery check;
- replacing the intended stable preview alias with an immutable deployment URL,
  digest, hash, or other stronger identity solely to satisfy smoke automation;
- blocking one provider's preview startup on another provider's full public
  read-surface convergence.

The accepted stopping rule is simpler: a successful provider deployment command
is sufficient for automation. At most, a later independent smoke may assert that
one representative URL does not return `404`; it must not become a prerequisite
for the Peer preview to start. If that low-cost check is unreliable, remove it
rather than adding resilience machinery.
