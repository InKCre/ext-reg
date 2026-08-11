# MVP Review Control Surface

## Working Mode

This review proceeds as a repeated loop:

```text
reported concern -> evidence -> diagnosis -> bounded design review
-> accepted disposition -> impact handshake -> batched remediation -> verification
```

- Before requesting review, the agent independently develops an evidence-backed
  solution for the whole adjacent problem batch, including trade-offs, failure
  behavior, and implementation impact.
- One conversation round may cover several small decisions when they form one
  coherent state diff. Do not fragment them into a sequence that makes Sir
  design the solution through answers.
- Sir reviews the proposed batch. Pause only for a material product choice,
  missing user-owned information, or explicit authorization boundary.
- A working implementation is evidence of behavior, not proof of a sound design.
- Sir's statements and prior agent decisions are both reviewable inputs, not automatic authority.
- Review files own task-local diagnosis. Accepted durable changes must update their canonical code, schema, tests, automation, or design owner during remediation.
- No implementation batch starts until its intended state diff and blast radius are explicit.

## Batch Queue

All batches use the terms in [Vocabulary Alignment](00-vocabulary-alignment.md).

| Batch | Scope | Status |
| --- | --- | --- |
| [01](01-deployment-state-and-target-identity.md) | Shared installed Release, enabled Peer set, Distribution state, table shape | Remediated locally; exact-image delivery pending |
| [02](02-language-neutral-runtime-contract.md) | Platform-specific Host SDK/API shapes | Remediated locally; exact-image delivery pending |
| [03](03-artifact-contract-and-hosting.md) | Native Distribution surfaces and Registry hosting responsibility | Remediated and locally verified |
| [04](04-legacy-and-implementation-simplification.md) | Legacy isolation, hard cutover, implementation depth, and CI/CD simplification | Remediated locally; remote cutover pending authorization |
| [05](05-native-implementation-integrity.md) | Native admission, database authority, runtime teardown, and delivery race audit | Remediated and independently verified |
| [06](06-ci-and-preview-delivery.md) | Locked Core CI parity and isolated Registry PR preview delivery | Locally verified; preview infrastructure configuration pending |

## Disposition Vocabulary

- **Confirmed**: evidence supports the concern.
- **Partially confirmed**: the concern identifies a real issue but the proposed cause or remedy needs correction.
- **Not reproduced**: current evidence does not support the concern.
- **Accepted redesign**: a replacement design has been reviewed and accepted.
- **Remediated**: canonical owners changed and the bounded verification passed.
