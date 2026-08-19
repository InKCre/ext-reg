# Adjacent Batches — Runtime alignment

- **Status:** planned; each source batch requires its own start authorization
- **Authority:** active Impact Handshake
- **Supersedes:** the automatic A→G progression implied by plan `81`
- **Evidence:** active final findings and plan

| Batch | Coherent change | Exit condition | Next gate |
| --- | --- | --- | --- |
| 1 | ext-reg contract generation + installed-wheel metadata + Toolkit finalizer | generated bindings are clean; one finalized wheel is discoverable from installed metadata | review, then authorize Batch 2/3 |
| 2 | Python Runtime + Core compatibility slice | Runtime owns manager/base/native lifecycle; Core rich model and local-wheel integration pass; local hit performs no Registry work | review, then authorize Batch 4 publication |
| 3 | Web Runtime + Client compatibility slice | Runtime owns manager/module lifecycle; Client rich model and local-tarball integration pass without UI/DB duplication | review, then authorize Batch 4 publication |
| 4 | independent Toolkit/Runtime releases | immutable native package assets exist after explicit publication authorization | authorize release-lock normalization |
| 5 | replace temporary local package inputs with released PDM/pnpm locks | both Peer repositories pass their full checks using only released Runtime/Toolkit assets | review and preview authorization |
| 6 | preview acceptance | normal Core/Client preview deployment works; local-hit and fresh-miss paths are observed; setup popup opens | Sir product acceptance |

Batch 2 and Batch 3 may be implemented in parallel only after Batch 1's
contract is accepted. They deliberately include their Peer compatibility slice
before publication, using a local wheel/tarball in a disposable install. This
breaks the release bootstrap cycle without introducing an adapter or committing
an absolute/local dependency. Batch 4 is not implied by successful local
builds. Batch 5 begins only after each native asset is published and lockable
through PDM/pnpm.
