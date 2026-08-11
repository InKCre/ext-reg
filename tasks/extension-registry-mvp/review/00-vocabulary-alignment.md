# Review Vocabulary Alignment

## Purpose

Use established package-registry and Module Federation language where it fits.
Avoid custom abstractions that force every Runtime Adapter to understand one
generic artifact protocol.

## Canonical Product Terms

| Term | Meaning in InKCre | Example |
| --- | --- | --- |
| **Extension** | The logical plugin product registered under one canonical Extension Name. | Twitter Extension |
| **Extension Name** | The globally unique, immutable Registry identity of an Extension. The ownership scope is part of the name, not a second product identity. | `inkcre/twitter` |
| **Extension Nickname** | Mutable human-facing product nickname; never identity. | `Twitter` |
| **Extension Release** | One versioned snapshot of an Extension. A release may publish several Distributions. | `inkcre/twitter@0.1.0` |
| **Extension Distribution** | The format-specific unit built by a producer, hosted by the Registry, and downloaded/installed or loaded by a consumer. | Python wheel; Module Federation Remote |
| **Distribution Format** | The established packaging/integration technology used to publish and consume a Distribution. | Python wheel; Module Federation Remote |
| **Distribution Descriptor** | Pre-download metadata through which a consumer discovers the Distribution Format, native locator, and compatibility information. It may be a format-native document rather than one generic Registry schema. | Python index/Core Metadata; MF manifest |
| **Distribution Compatibility Contract** | The complete pre-download contract used to decide whether a Distribution can be consumed: Distribution Format, format-native compatibility metadata, and Extension API compatibility. It is a concept, not necessarily one additional file. | Wheel tags + `Requires-Python` + API SDK dependency; MF manifest/shared metadata |
| **Distribution Metadata** | Format-native metadata needed to resolve and consume a Distribution, including its producer-declared compatibility conditions. | Wheel metadata/tags; MF manifest |
| **Distribution File / Asset** | A physical hosted file belonging to a Distribution. | `.whl`; `remoteEntry.js`; JS chunk |
| **Content Digest** | Integrity identity of physical content. It is Registry/storage/native-protocol metadata, not deployment product state. | SHA-256 of a wheel or immutable remote content |
| **Extension Registry** | The public index and distribution service that owns Extension Names, Releases, publication policy, and hosted Distributions. | InKCre Extension Registry |

The phrase “the thing built and hosted by the Registry that a Peer downloads
and consumes” means **Extension Distribution**. Use **Distribution Artifact**
only when emphasizing its physical bytes. Before publication, CI may call its
output a **build artifact**; after Registry admission it is a Distribution.

## Actors And Runtime Terms

| Term | Meaning |
| --- | --- |
| **Producer** | Builds a Distribution. In Module Federation this is the Remote/Producer. |
| **Publisher** | Is authorized to publish an Extension Release or Distribution to the Registry. Often the producer's CD pipeline. |
| **Consumer** | Downloads, installs, or loads a Distribution. In Module Federation this is the Host/Consumer. |
| **Peer** | An InKCre runtime participant that may host Extensions. |
| **Extension Runtime** | The language/runtime-specific implementation of the Extension lifecycle contract. |
| **Extension Runtime Adapter** | Bridges one Peer environment and one format-native Registry surface: resolve, acquire, install/load, lifecycle, and cleanup. |

## Operation Terms

```text
source -> build Distribution -> publish to Registry
Registry -> resolve Distribution -> download/fetch
Runtime Adapter -> install or load -> enable -> run
```

- **Publish** changes Registry state.
- **Resolve** selects a format-compatible Distribution of an exact Extension Release.
- **Preflight** evaluates the Distribution Compatibility Contract from its
  Descriptor before fetching executable Distribution bytes.
- **Install/materialize** places a Python or other installable Distribution into its runtime environment.
- **Load** is the more accurate Module Federation operation.
- **Enable/disable** changes Deployment/Peer lifecycle state, not Registry state.

## Compatibility Language

There is no producer-capabilities/consumer-requirements dual contract.

- A Distribution declares one-direction **compatibility conditions** as its
  Distribution Compatibility Contract, describing the environments in which it
  can be consumed.
- A Runtime Adapter compares those conditions with its actual environment or
  delegates that work to format-native tooling such as Python packaging or a
  Module Federation Host.
- “Capabilities digest” is not a canonical term and should not be introduced.

## Terms To Retire Or Narrow

- **Extension Coordinate**: retire; use Extension Name. A Registry may split a
  scoped name into internal columns for authorization and indexing, but the
  product exposes one name rather than two identities.
- **Target**: retire from the product model; use Extension Distribution. It may
  remain a build-tool-local term.
- **Target key**: retire; native Distribution identity and Registry records
  should not require a publisher-invented cross-format slot name.
- **Artifact format**: prefer Distribution Format.
- **Extension artifact**: acceptable informal shorthand, but ambiguous between
  a Distribution and one physical file. Use the precise term in contracts.
- **Canonical target manifest**: do not assume one public cross-format manifest.
  Use Extension Release metadata plus format-native Distribution metadata;
  Registry-internal canonical storage metadata is an implementation detail.

## Distribution Identity

There is no universal public cross-format Distribution ID.

- A Python Distribution is identified and resolved through Python package-index
  conventions, including its Distribution filename and native metadata.
- A Module Federation Distribution is identified and resolved as a Remote
  through its Registry URL and native MF manifest/remote entry.
- A Registry database may use an opaque surrogate row ID internally, but that
  value is not product vocabulary or a Peer integration contract.
- A content digest identifies exact bytes for integrity; it is not the semantic
  Distribution name.
- Compatibility conditions are Distribution metadata. They are neither an ID
  nor an input to a “capabilities digest”.

## External Alignment

- PyPA defines a Project as having Releases, with each Release comprising one or
  more Distributions; a Distribution Archive is the physical file.
- PyPA calls a wheel a Built Distribution and a package index a repository of
  Distributions for automated discovery and consumption.
- Module Federation defines Producer/Remote, Consumer/Host, and a generated MF
  Manifest describing the remote entry, exposed modules, assets, shared
  dependencies, and types.
