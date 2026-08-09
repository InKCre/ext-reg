# Roadmap And Work Structure

## Phase 0 — Task Control Surface

- **Status**: Complete.
- Git, SVC, instructions, docs navigation, and this poly-file packet exist. This is not the executable project foundation.

## Phase 1 — Product Design

- **Status**: Complete.
- [`15-product-design.md`](15-product-design.md) defines the admitted public Registry, publisher, release, compatibility, deployment lifecycle, trust promise, MVP workflows, and non-goals.

## Phase 2 — High-level Technical Design

- **Status**: Complete.
- Choose the smallest production topology, authoritative data model, Registry API, artifact representation, publisher auth, Runtime/API package boundary, deployment install lock, peer admission paths, and operational flow.
- Compare Cloudflare and GitHub primitives using official evidence and name only design-changing technical risks.

## Phase 3 — Targeted Risk PoC

- **Status**: Complete.
- Cloudflare Python Worker + FastAPI + D1 + R2 passed locally and remotely.
- A relative-base Module Federation remote passed a cross-origin immutable-prefix browser load and full lifecycle call.
- Evidence is in [`work/09-hld-pocs.md`](work/09-hld-pocs.md).

## Phase 4 — Implementation Plan And Preflight

- **Status**: Complete.

- Map exact files and owners across `ext-reg`, fresh `core-py origin/main`, and fresh `client-web origin/main` worktrees.
- Rehearse publish, install, enable, disable, uninstall, deployment ordering, data migration, credentials, failure rollback, and verification before code mutation.

## Phase 5 — Project Foundation And Registry

- **Status**: Complete.
- Executable Python/TypeScript foundation, service, contracts, metadata migration, artifact flow, publisher CLI, Runtime/API package, focused checks, package builds, Pyodide build, and local Worker black box are complete.
- Repository CI/CD, public remote, production resources, production deployment, scoped publication, and public smoke are complete.

## Phase 6 — Peer Integration And Publisher CD

- **Status**: Complete.
- Both peer adapters were migrated from fresh `origin/main` worktrees.
- Each peer owns its first-party target build/publication while preserving application delivery.
- The shared installation and per-peer binding model, lifecycle APIs, UI, and uninstall guard are deployed.

## Phase 7 — Production Acceptance

- **Status**: Complete.
- Public Registry and both peers are deployed; both targets are published under one Extension Version.
- The real Chromium/shared-database lifecycle journey in [`50-acceptance.md`](50-acceptance.md) passed with zero final residue.

## Work File Convention

- `packet.md` is the current status/next-action surface.
- Files `10` through `50` own evidence, product, decisions, HLD, roadmap, and acceptance.
- A bounded design, PoC, or execution slice receives one file under `work/`; it closes when its facts move to the appropriate owner.
