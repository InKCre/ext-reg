# Review Batch 03 — Artifact Contract And Hosting

## Scope

- Show how a canonical target manifest is produced, serialized, uploaded, stored, and addressed.
- Explain and reassess `artifact_format` versus integration/API compatibility declarations.
- Decide the common control-plane model and format-native distribution surfaces, initially a PyPI-compatible Python API and an immutable Module Federation remote API.
- Diagnose whether embedding the Python target bundle in the Core application image violates the Registry's hosting responsibility.
- Redesign Python target delivery without introducing arbitrary uncontrolled runtime execution.

## Opening Evidence

- The Python Packaging Simple Repository API already defines HTML and JSON
  project indexes, normalized project names, distribution-file links,
  `Requires-Python`, separately served core metadata, yanking, hashes, and
  provenance. Python consumers can use this protocol directly rather than a
  Registry-specific target manifest:
  <https://packaging.python.org/en/latest/specifications/simple-repository-api/>.
- Module Federation can generate `mf-manifest.json` as a runtime-oriented
  manifest containing its remote entry, exposes, shared dependencies, assets,
  and type URLs. An MF Host can register that manifest URL directly and resolve
  the remote entry/assets from it:
  <https://module-federation.io/guide/basic/manifest-snapshot>.
- The current generic canonical target manifest duplicates both ecosystems'
  native Distribution descriptors. Its digest/file index may remain internal
  storage and integrity machinery, but it is not justified as a public
  cross-format consumer contract.

## First Design Surface

The opening recommendation is one common Registry control plane for Extension
Name, Release, publisher, and lifecycle, plus format-native Distribution
surfaces beneath each Release:

```text
Python Distribution -> Simple Repository API + wheel/core metadata
Web Distribution    -> mf-manifest.json + remoteEntry/assets
```

The Host SDK selects the native surface it implements and delegates acquisition
to its Python packaging or Module Federation consumer. Internal object IDs,
digests, and file manifests remain Registry implementation details unless a
native protocol exposes them.

This design surface is accepted.

## Second Design Surface — Python Acquisition Timing

The current Core integration embeds a custom ZIP target bundle and catalog in
the Core application image. That makes the Peer's CD, rather than the Registry,
the effective availability boundary for the Python Distribution and bypasses the
accepted Python package-index consumer path.

The next recommendation is that the Core Host SDK acquire the exact installed
Extension Release's compatible wheel from the Registry when enabling the
Extension or restoring it on cold start:

```text
shared extensions row (exact Release)
  -> Core Host SDK queries Registry Simple API
  -> Python Distribution Consumer selects compatible wheel/metadata
  -> installs into a Host SDK-managed local environment/cache
  -> discovers Extension through its Python entry point
  -> invokes on_start
```

The local environment/cache is replaceable execution material, not deployment
authority. Peer CD publishes the first-party wheel to the Registry but does not
copy that wheel into the Core image. Registry unavailability may therefore block
enable or cold restore; it does not rewrite installed/enabled intent.

This accepts privileged in-process Extension execution but removes the custom
embedded bundle. Dependency-environment construction and atomic replacement are
later implementation questions; this design surface asks only whether online
Host SDK acquisition is the Python MVP ownership boundary.

This design surface is accepted.

## Dismissed Design Surface — Python Extension Environment

In-process Python Extensions share one interpreter and `sys.modules`. Separate
per-Extension install directories would not provide real dependency isolation,
while installing third-party packages directly into Core's immutable base
environment would blur ownership and make cold-start reconstruction difficult.

The previous recommendation for a separate Host SDK-managed shared environment
is withdrawn. It was not a security boundary, could not isolate modules inside
one interpreter, and duplicated responsibilities already carried by Python
packaging metadata and the Core runtime.

The smaller contract is:

- `Requires-Python` declares interpreter-version compatibility;
- wheel Python/ABI/platform tags declare executable-platform compatibility;
- `Requires-Dist` and environment markers declare Python dependencies;
- the producer-declared Core Host SDK range declares Extension API
  compatibility;
- the Python installer resolves these against the real Core environment before
  the Host SDK loads the entry point.

Extensions are trusted in-process packages and naturally share Core's Python
runtime. The Registry must faithfully serve and validate native metadata; it
does not prescribe an environment topology. Concrete installer commands,
filesystem locations, caches, and cleanup remain Core implementation details and
are not product choices in this review.

This surface is closed without a new environment abstraction.

## Fourth Design Surface — Native Distribution Association

The mapping does not require a target key or generated cross-format ID. Producer
source metadata already has an appropriate extension point:

```toml
[project]
name = "inkcre-ext-twitter"       # Python project identity
version = "0.1.0"

[project.entry-points."inkcre.core.extensions"]
default = "inkcre_twitter:Extension"

[tool.inkcre-extension]
name = "inkcre/twitter"           # canonical Extension Name
nickname = "Twitter"
core = ">=0.1.0,<0.2.0"           # Host SDK compatibility
```

The exact table/key spelling remains an implementation contract, but the
authority flow is accepted:

```text
producer source metadata
  -> publisher reads custom Extension fields
  -> verifies built native metadata/entry
  -> Registry associates native Distribution with Extension Release
  -> Host SDK resolves from Registry; it never parses producer pyproject.toml
```

Arbitrary `[tool.*]` data is not automatically copied into wheel Core Metadata.
That is desirable here: it is publisher input, while the Registry association
is the consumer-visible authority. Web publication follows the same pattern
using package/build metadata and verifies the generated MF manifest.

Existing Core extensions demonstrate the pattern but need normalization:
Twitter uses `[tool.inkcre-ext]`, GitHub uses `[inkcre-ext]`, RSS omits its ID,
and all are currently marked `distribution = false`. Those are remediation
facts rather than reasons for another manifest.

## Status

Accepted redesign. Format-native surfaces, online Core acquisition, native Python
metadata, and producer-declared native Distribution association are accepted in
direction. Native Distribution version congruence, publication, hosting,
consumption, and the three-repository destination boundary are accepted as one
integrated state diff. Implementation remains unchanged until Batch 04 defines
and receives approval for the cutover.

## Integrated Recommendation

### 1. Keep One Small Common Control Plane

The Registry control plane owns only the product relationship that Python and
Module Federation cannot express together:

```text
Extension Name + Nickname
  -> Extension Release + lifecycle
    -> native Distribution associations + publisher provenance
```

For the MVP, one Release may associate one Python project release and one
Module Federation Remote snapshot. A Python project release may contain several
native files such as platform-specific wheels. This is not a generic target
model: the two association kinds have different native schemas and endpoints.

A public Release response should be shaped conceptually as follows; exact field
and path spelling belongs to HLD/API work:

```json
{
  "name": "inkcre/twitter",
  "nickname": "Twitter",
  "version": "0.1.0",
  "state": "published",
  "distributions": {
    "python": {
      "project": "inkcre-ext-twitter",
      "index": "/simple/inkcre-ext-twitter/",
      "host_sdk": "core-py",
      "host_sdk_version": ">=0.1.0 <0.2.0"
    },
    "module_federation": {
      "manifest": "/extensions/inkcre/twitter/0.1.0/module-federation/mf-manifest.json",
      "host_sdk": "@inkcre/core",
      "host_sdk_version": ">=0.1.0 <0.2.0"
    }
  }
}
```

The native project/Remote name is a format-specific locator, not another
Extension identity. The Host SDK identity and version range express the
already-accepted Extension API compatibility. There is no `target_key`,
`artifact_format`, generic conditions array, capabilities digest, or public
canonical target manifest.

### 2. Publish Python Through A Python Package Index

The Registry implements the standards-based Simple Repository API for reads and
a PyPI-compatible upload endpoint for writes. This permits standard tooling such
as `uv publish` or Twine to upload wheels and Python installers to resolve them.
The Registry exposes native filename, hash, `Requires-Python`, wheel tags, and
Core Metadata rather than translating them into Registry conditions.

Python source metadata supplies the missing product association:

```toml
[project]
name = "inkcre-ext-twitter"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["twikit>=2.3.3"]

[project.entry-points."inkcre.core.extensions"]
default = "inkcre_twitter:Extension"

[tool.inkcre-extension]
name = "inkcre/twitter"
nickname = "Twitter"
host-sdk = "core-py"
host-sdk-version = ">=0.1.0,<0.2.0"
```

The publisher performs a small control-plane preparation/association call using
the custom table, then uploads the built Distribution through the native upload
API. Registry tooling may orchestrate these two steps for DX, but it must not
replace `uv build`, `uv publish`, wheel metadata, or Simple API consumption with
a custom ZIP/manifest protocol.

The PyPI upload protocol accepts one file at a time. Therefore the Registry
stores uploaded files privately while a Release is preparing, and only exposes
them in the public Simple index when the parent Release is published. After a
Release is public, a distinct additional wheel filename for the same native
project/version may be appended; retrying identical bytes is idempotent, while
the same filename with different bytes is rejected.

### 3. Publish Web As One Immutable MF Remote Snapshot

Web source uses equivalent package/build metadata for Extension Name, Nickname,
Release version, Host SDK identity, and Host SDK range. Its build produces an
MF-native `mf-manifest.json`, remote entry, and referenced assets.

There is no generally adopted MF Registry upload protocol, so the Registry
publisher accepts one Remote directory/archive, validates that the MF manifest
and all referenced local assets form a closed traversal-free snapshot, then
atomically exposes the snapshot beneath its immutable Extension Release URL.
The Module Federation Host consumes that manifest URL directly. A Release may
associate one immutable MF Remote snapshot in the MVP; replacing it requires a
new Extension Release, while an identical retry is idempotent.

Internal file rows, hashes, temporary upload sessions, and content-addressed R2
keys remain legitimate integrity/storage mechanisms. They are deliberately not
public Distribution identity, deployment state, or a second generic manifest.

### 4. Share Version Semantics, Not Upload Timing

Every associated native Distribution is version-congruent with its Extension
Release. Stable versions use the same `MAJOR.MINOR.PATCH` spelling. For Python
pre-releases, the Registry accepts only an explicit lossless mapping between its
supported SemVer spelling and normalized PEP 440 metadata; arbitrary SemVer
pre-release labels that cannot be represented by Python are not associable with
a Python Distribution.

An authorized publisher may publish an Extension Release once at least one
native Distribution association is ready. Another format may be appended later;
there is still no producer-declared required-format set. A deployment decides
whether all currently enabled Peers have a usable native Distribution before an
install-version change. Publication does not claim universal Peer coverage.

Once public, product metadata and an existing native association are immutable.
Corrections use a new Extension Release. `yank` removes the Release from new
selection without mutating deployments; an operator block may deny new download
while retaining the audit record. Permanent byte retention remains outside the
product promise, as already accepted.

### 5. Registry Owns Hosting; Host SDKs Own Consumption

The Registry metadata database owns Extension, Release, native Distribution
association, publisher authority, lifecycle, and provenance. Registry-managed
object storage owns all wheel and MF Remote bytes. A Peer CD uploads bytes but
does not become their production availability boundary.

At runtime:

```text
shared extensions row: inkcre/twitter@0.1.0 + enabled Peer UUIDs
  -> platform Host SDK reads exact Release descriptor
  -> checks its own Host SDK version range before executable bytes
  -> delegates to its native Distribution Consumer
     Core: Python index/installer + entry point
     Web: Module Federation Host + MF manifest
  -> calls that platform's lifecycle
```

Install records the shared exact Release and starts disabled. A new enable adds
the Peer UUID only after preflight, acquisition/load, entry validation, and
profile-specific start all succeed; failure leaves that Peer disabled. A cold
start may resolve native bytes again because no binding table or digest is
persisted. Missing native format, incompatible Host SDK range, native
installer/Host rejection, or Registry outage then prevents `running` but retains
the previously authorized installed version and enabled intent for diagnosis or
retry.

### 6. Remediation State Diff

`ext-reg`:

- replace `targets`, target keys, generic conditions, `artifact_format`, and the
  public target manifest/file API with Extension/Release plus typed Python and
  MF association records;
- add Simple Repository reads, PyPI-compatible upload, immutable wheel serving,
  and an MF Remote snapshot upload/serve path;
- replace `publish-target` with native association/publish orchestration;
- retire the generic Python client/matcher and `runtime-web` matcher/lifecycle
  package surfaces that belong in platform Host SDKs;
- keep publisher auth, release lifecycle, D1 authority, R2 hosting, provenance,
  content verification, and public smoke evidence.

`core-py`:

- migrate the existing `extensions` row to canonical Extension Name while
  preserving shared version/config/schema/`enabled[]` semantics;
- remove the parallel installation/binding tables, embedded target catalog,
  custom ZIP loader, Docker bundle copy, and corresponding target CD path;
- make `ExtensionBase`/Host SDK resolve the associated Python project, use
  Python packaging to acquire the exact release, discover the standard entry
  point, then preserve Core's `on_start/on_close` behavior;
- normalize first-party `pyproject.toml` metadata and publish wheels through the
  Registry without special first-party semantics.

`client-web`:

- return installation/enablement to the shared `extensions` row and remove
  binding/target-matcher integration;
- resolve the Release's MF association, precheck the declared `@inkcre/core`
  Host SDK range, and give the immutable manifest URL to the MF Host;
- publish Twitter's complete MF Remote snapshot from its existing peer-owned
  source while retaining local joint-development behavior.

This is intentionally a replacement of the current generic target architecture,
not an adapter layered on top of it. CI/CD is simplified to native builds,
native publication, Registry black-box verification, and existing Peer checks;
the cross-format manifest/digest conformance matrix is deleted.

## Batch Review Boundary

Review this recommendation as one state diff. Objections should identify which
of the following product boundaries is wrong: the small common control plane,
the native Python surface, the native MF surface, publication/immutability, Host
SDK consumption, or the three-repository removal plan. Exact endpoint names,
table columns, upload-session mechanics, cache paths, and installer commands are
HLD/implementation details after this batch closes.

## Sources

- Python Simple Repository API:
  <https://packaging.python.org/en/latest/specifications/simple-repository-api/>
- Python Core Metadata:
  <https://packaging.python.org/en/latest/specifications/core-metadata/>
- Python entry points:
  <https://packaging.python.org/en/latest/specifications/entry-points/>
- Python wheel compatibility tags:
  <https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/>
- PyPI Upload API: <https://docs.pypi.org/api/upload/>
- `uv` build and publish workflow: <https://docs.astral.sh/uv/guides/package/>
- Module Federation manifest and snapshot model:
  <https://module-federation.io/guide/basic/manifest-snapshot>
