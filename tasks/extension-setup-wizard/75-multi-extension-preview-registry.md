# Multi-Extension Static Preview Registry

## Why This Follow-up Exists

Client PR preview currently combines three outputs from `Client checks` into one
Cloudflare Pages deployment:

1. the Client SPA;
2. a generated exact `inkcre/twitter` Release descriptor;
3. the Twitter Module Federation manifest and asset closure.

The resulting HTTP topology is useful and inexpensive. The workflow topology is
not accepted: validation checks must not produce and upload deployable SPA/MF
outputs for a later `workflow_run` delivery to download. The same-origin result
remains desirable. The
same origin behaves as a bounded, read-only Registry facade, so the Web Host can
exercise its real Release lookup and Module Federation loading path without a
per-PR Worker, D1 database or R2 bucket.

The ownership is wrong. `client-web` currently owns a Twitter-specific assembly
script that knows Registry URLs, Release JSON shape, native association fields,
manifest materialization and response headers. Those rules can drift from the
Registry service and will otherwise be copied into every Peer repository.

## Accepted Direction

The **Extension Developer Toolkit**, owned and released by `ext-reg`, provides the
static Preview Registry builder. It is a build-time/development tool, not an
Extension Host SDK, Runtime Adapter or runtime service.

A Peer repository may:

- build its Client application and Extension Distributions inside its isolated
  preview-delivery workflow from the verified exact pull-request head;
- call the Toolkit through its documented happy path;
- merge or mount the generated static tree into the output deployed by that same
  preview workflow run;
- host the result on Pages, another static host, or a local server.

A Peer repository must not:

- construct Registry Release descriptors;
- invent public Registry paths;
- rewrite native manifests using local protocol knowledge;
- maintain a format-specific clone of Registry validation.
- consume deployable SPA, MF, wheel or Preview Registry outputs uploaded by a
  pull-request checks workflow.

The hosting origin therefore does not imply Registry authority. A Client Pages
preview can legitimately host the generated facade while `ext-reg` remains the
contract and implementation owner.

## Multi-Extension Requirement

The Toolkit is not a one-Extension wrapper around the current Twitter script. One
invocation consumes an explicit set of Extension preview inputs and composes one
Registry tree containing zero or more native associations for every supplied
Release.

Conceptually:

```text
Preview input set
├── inkcre/twitter@0.2.1
│   └── module_federation -> extensions/twitter/dist/client-web
├── inkcre/rss@0.2.0
│   └── module_federation -> extensions/rss/dist/client-web
└── inkcre/github@0.3.0
    └── module_federation -> extensions/github/dist/client-web

Extension Developer Toolkit
  -> one deterministic static Preview Registry tree
```

The builder must:

- validate each canonical Extension Name, exact Release version, nickname,
  Host SDK association and native Distribution using Registry-owned models;
- allow multiple Releases and multiple Extensions in one output;
- reject duplicate natural keys with conflicting metadata or bytes;
- reject output-path collisions and traversal;
- materialize native public URLs against one explicit preview origin;
- emit only associations whose Distribution inputs were supplied;
- produce deterministic output independent of input ordering;
- leave application artifact assembly and hosting to the caller;
- allow each Peer preview to select only the native Distribution kinds that
  Peer consumes, while still supporting multiple Extensions per invocation.

It must not pretend to implement mutable Registry operations, credentials,
publish/yank state transitions, D1/R2 persistence or arbitrary API routes. It is
a bounded static projection for integration preview.

## Accepted Interface Direction

The command represents a set rather than one hard-coded Extension. The first
version uses an explicit, language-neutral JSON inventory because it makes
source inputs and cross-repository use visible:

```bash
inkcre-ext preview build \
  --inventory .preview/extensions.json \
  --public-origin https://preview-client-web-pr-71.example.pages.dev \
  --output .preview/registry
```

The inventory lists native Distribution inputs rather than copying Release
descriptors. Each item points to its producer metadata and exact-head build
output;
the Toolkit derives and reconciles canonical Extension Name, nickname, version and
Host SDK association through the same Registry-owned models used by admission.
Illustrative shape:

```json
{
  "schema_version": 1,
  "distributions": [
    {
      "kind": "module_federation",
      "producer": "extensions/twitter/package.json",
      "artifact": "extensions/twitter/dist/client-web"
    },
    {
      "kind": "python",
      "producer": "extensions/twitter/pyproject.toml",
      "artifact": ".preview/wheels/inkcre_extension_twitter-0.2.1-py3-none-any.whl"
    }
  ]
}
```

Exact field names remain an implementation detail until the Pydantic input
model and generated JSON Schema are reviewed, but these semantics are frozen:
one inventory, multiple Extensions, both native kinds, explicit inputs and no
implicit workspace scan. The CLI is added to the existing `inkcre-ext` entry
point under `preview build`; the library entry point accepts the same validated
inventory model.

## Expected Static Projection

For each supplied Release the output includes the same read paths the relevant
Host SDK actually consumes. Module Federation means:

```text
v1/extensions/<namespace>/<name>/releases/<version>
extensions/<namespace>/<name>/<version>/module-federation/
├── mf-manifest.json
├── remoteEntry.js
└── assets/*
```

Python support is part of the first slice, not a future extension. It emits the
bounded native read surface required by pip/Core:

```text
simple/
├── index.html
└── <normalized-project>/index.html
packages/<normalized-project>/<version>/
├── <wheel>.whl
└── <wheel>.whl.metadata
```

The Toolkit supports both native projections in its first version, but one facade
does not automatically contain both. The inventory controls the projection:

- a `client-web` preview carries exact Release descriptors containing only its
  supplied Module Federation associations and hosts their MF asset closures;
- a `core-py` preview delivery carries exact Release descriptors containing
  only its supplied Python associations and publishes their Simple pages,
  wheels and PEP 658 metadata built from the same exact PR head;
- either preview may carry multiple Extensions of its relevant native kind;
- a future combined integration host may supply both kinds explicitly.

This keeps each Peer preview self-contained without pretending that it is the
complete Registry. Both facades use the same canonical Extension name/version,
but each descriptor truthfully exposes only the bytes available at that preview
Registry origin.

For the browser, the facade should remain on the Client Pages HTTP origin: this
removes CORS and exercises the actual MF URL resolution path. For Core, “same
source” must not be confused with “same HTTP origin.” Core restores enabled
Extensions during application startup; if its Simple endpoint is served by the
same ASGI process, that process cannot fetch its own wheel before it begins
accepting requests. The minimum reliable topology is therefore a sibling
static Preview Registry origin produced and selected by the Core preview
delivery from the same verified PR-head build. Making it literally the Core
HTTP origin would require a pre-Core proxy/static server or a runtime bootstrap
change and is not justified for this facade.

## Core Sibling Hosting

The Core Python facade is deployed to **Cloudflare Pages**, not Heroku and not a
Worker/D1/R2 preview. It is static output and needs no process, database,
credential or mutable Registry lifecycle.

Use a dedicated Pages project, provisionally
`inkcre-core-py-extension-registry-preview`, owned operationally by the Core
preview workflow. Do not mix it into either the Client application project or
the ext-reg UI-preview project. A PR branch such as
`preview/core-py/pr-65` yields one stable sibling alias for that Core PR.

The Core preview sequence is:

1. The trusted Core preview controller verifies an eligible same-repository PR
   and checks out its exact head separately from the controller source.
2. That preview workflow installs the frozen Core/Toolkit environment, builds
   all first-party wheels and writes the multi-Extension inventory.
3. `inkcre-ext preview build` writes the static exact-Release/Simple/wheel tree
   using the deterministic PR-specific Pages alias as its public origin.
4. The same workflow run deploys that tree directly to the dedicated Core
   Registry-preview Pages project; no checks artifact is uploaded or downloaded.
5. Delivery verifies Wrangler returned the expected stable alias, smoke-reads
   it, and confirms the recorded PR head.
6. Delivery configures the Core Heroku preview's Registry origin to that alias
   before the Core app starts, then deploys/starts Core.
7. PR close cleanup retires the exact Pages branch alias together with the Core
   Heroku and preview-database resources.

The facade should contain all first-party Python Extensions built by that Core
preview run, not only Twitter. This supports restoring any Extension already
enabled in the preview database and exercises the accepted multi-Extension
path. No Registry token is exposed to Core; all reads are public immutable
preview bytes.

The first slice does not need the Registry catalog/list API because current
Host integration resolves an already installed exact name/version.

## Drift Prevention

The static builder must not maintain a parallel implementation of the public
Registry API. `ext-reg` already owns the relevant executable components:

- `contracts.models.ReleaseRecord` and native association models;
- Python wheel/Core Metadata inspection;
- PEP 503 Simple HTML serialization (the static host has no `Accept`
  negotiation; the Worker retains PEP 691 JSON);
- PEP 658 metadata projection;
- Module Federation snapshot inspection and public-path materialization;
- public path construction in the Registry service.

Implementation first extracts any request-handler-local projection into pure
Registry application functions. The Worker handlers and Preview builder then
call those same functions. The builder may replace D1/R2 repositories with an
in-memory/static output sink, but it must not replace Registry models or
serializers.

## Preview Workflow Authority

Organization governance distinguishes pull-request validation from isolated
preview delivery. The corrected Preview Registry plan follows that boundary:

- required checks remain merge evidence and do not upload deployable preview
  outputs for another workflow to consume;
- the preview controller runs from trusted base-repository workflow code,
  verifies the exact same-repository pull-request head, then builds and deploys
  that head in one preview workflow run;
- the Client preview builds both the SPA and all supplied MF snapshots there,
  invokes the Toolkit into the SPA output, and deploys that directory directly;
- the Core preview builds all supplied wheels and the Python facade there,
  deploys the sibling Pages origin, then delivers Heroku with that origin;
- preview credentials are scoped to the `preview` environment and appear only
  in delivery steps; fork pull requests receive no preview credentials;
- pull-request close cleanup remains a separate trusted controller because it
  owns resource retirement rather than candidate build output;
- diagnostic artifacts may still be uploaded on check failure, but no preview
  workflow may treat them as deployable input.

This removes the rejected `Client checks -> upload-artifact -> workflow_run ->
download-artifact -> Pages` chain. It also avoids treating an independently
rebuilt check output as byte-identical delivery evidence.

The public origin is a deterministic PR branch alias known before the Toolkit
runs. For example, the Core facade can use a simple Pages branch `pr-65` and the
corresponding project alias. The workflow must compare Wrangler's reported alias
with that expected value and fail before Heroku delivery on mismatch. A random
Pages deployment URL is useful as deployment identity, but cannot become the
embedded public origin after the static output has already been generated.

Drift is prevented by this shared executable path, not by adding a second test
matrix that compares Worker and static output. Sir explicitly rejected a new
differential test and any other new test in this follow-up. Existing Registry
contract checks and existing Peer preview smoke paths remain; implementation
does not add test files or test cases for the builder migration.

## Repository Consequences

### `ext-reg`

- owns the reusable builder and its Registry-native validation/serialization;
- validates multiple Extensions, input-order determinism, collisions and
  native manifest materialization inside the reusable command;
- publishes the builder through the independent Extension Developer Toolkit
  distribution.

### `client-web`

- deletes the Twitter-specific Registry assembler after adopting the Toolkit;
- supplies the multi-Extension inventory and builds exact-head SPA/MF inputs in
  the preview workflow itself;
- replaces the checks-artifact `workflow_run` handoff with a trusted,
  same-repository exact-head preview controller and direct Pages delivery;
- verifies the final preview URL as a consumer, without revalidating Registry
  internals.

### `core-py`

- builds Python wheels for the Extensions included in its preview inside the
  existing trusted preview delivery workflow;
- publishes the Toolkit-generated exact Release, Simple HTML, wheel and PEP 658
  tree as a sibling preview origin selected from the same exact PR head;
- configures that Core preview to resolve this preview-owned facade rather than
  a Client Pages origin or production Registry;
- does not add static Registry routes or a bootstrap dependency to production
  Core runtime.
- deploys the static tree to a dedicated Cloudflare Pages project before
  starting the Heroku preview and retires its PR branch during preview cleanup.

### Other Peers

- may reuse the same command for local or PR integration preview;
- do not need to adopt Pages or copy Client workflow structure;
- do not gain Registry runtime authority.

## Implementation Status

Sir explicitly started implementation after accepting the delivery sequence.
The first local implementation proves the v1 inventory model, generated schema,
multi-Extension static sink and `inkcre-ext preview build` CLI. It reuses the
existing Release models, wheel inspection, Simple HTML serializer and MF
snapshot inspector; no new test was added. The existing full Registry contract
passes. The code is currently in the Registry package only as a local
implementation artifact and must move before release. Client and Core adoption
consume `inkcre-extension-toolkit 0.1.0` rather than pinning a source commit or
installing the Registry service package. Both use root PDM projects plus
`pdm.lock`; Client's root pnpm workspace continues to own its application and
Extension JavaScript dependencies. Both workflows execute only their frozen
local tooling environment; uv is not used.

The earlier adoption sequence incorrectly assigned SPA/MF/wheel construction to
checks and used uploaded artifacts as delivery inputs. D040 supersedes that
workflow detail. Required-check semantics remain independent merge evidence,
while deployable preview uploads are removed from checks. Both Peer preview
workflows build and deploy their own exact-head outputs in one run.

## Core PR #65 Distribution Provenance Finding

The Core preview image does not contain first-party Extension source or wheels:
its Dockerfile copies only Core application/runtime/database files. At runtime,
`PipDistributionConsumer.acquire()` either discovers an exact Distribution
already installed in that interpreter or resolves the exact Registry Release,
downloads one wheel through the Release's Simple index and installs it into the
Core environment.

Consequently, Core PR #65 did not install `twitter@0.2.0` from the Client Pages
facade: that facade explicitly rejected and omitted a Python association. The
Core process could only have acquired the wheel while another configured
Registry origin exposed the Python association, or reused it within the same
still-running dyno after such acquisition. A redeployed dyno cannot rely on
that ephemeral installed wheel.

The current read-only production query returns:

```text
GET https://registry.inkcre.dev/v1/extensions/inkcre/twitter/releases/0.2.0
404 {"detail":"public Release does not exist"}
```

Core first-party publish workflow history inspected for the relevant main
revision did not publish Twitter `0.2.0`; its Twitter job selected a no-op. The
older task result also recorded `0.2.0` publication as a later action. Available
evidence therefore does not identify the transient remote mutation that made
the successful black-box run possible. This is recorded as an audit-evidence
gap rather than attributing it to the PR image or inventing provenance. The new
static Preview Registry removes that ambiguity by carrying the native
Distributions built by the exact preview head and their source inputs in one
inventory.

Source implementation is authorized. Commit, push, Toolkit publication, peer
workflow push and remote preview mutation still require their separately
governed authorization.
