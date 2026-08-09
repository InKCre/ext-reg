---
name: svc
description: Use the local Sustainable Vibe Coding CLI to bootstrap, inspect, and evolve a project without copying framework documents. Trigger for SVC guidance, project adoption, or safe SVC CLI use; do not use it to replace consumer-owned project truth.
---

# Sustainable Vibe Coding

SVC is a versioned, local knowledge corpus plus a small development-collaboration CLI. Its canonical guidance stays inside the installed `svc` distribution. This project owns its own product truth, technical decisions, task packets, and unmarked documentation.

## Start With Status

Run `svc status --json` when beginning work that may depend on SVC. It distinguishes the installed CLI/corpus version from the version this project has adopted in `svc.json`, and reports invalid schema-v2 configuration, missing or user-modified generated guidance, and the managed local-config ignore block without claiming authority over project content.

## Find Canonical Guidance

Use `svc lookup --keyword "<need>" --json` to search locally and deterministically. Use the returned path with `svc lookup --name '<escaped-exact-path>' --json` to read the document. `--name` is a full-path regular expression over source-relative SVC paths; use `--all` only when several documents are intended. Prefer this two-step lookup over remembering or reproducing SVC rules from this skill.

## Bootstrap or Repair Integration

Use `svc init --agent codex <repo> --json` to inspect a non-mutating plan. Apply only the returned exact digest with `--apply <digest>`. Init may create `svc.json`, this skill, and bounded navigation blocks in root `AGENTS.md` and `docs/index.md`, plus a marked `.gitignore` entry for `svc.local.json`; it never silently overwrites unmarked consumer content or a modified generated surface. Schema-v1 projects are write-blocked: migrate the configuration deliberately.

## Declare Development Capabilities

`svc.json` schema v2 is a complete, committed configuration. Its optional `dev` section selects a profile and declares named targets. Each target has a scope (`worktree`, `repository`, or `host`), one readiness probe (`http`, `tcp`, or `exec`), and an `exec` or `manual` provisioner. Keep machine- or worktree-specific `dev` values in the optional ignored `svc.local.json` overlay. It merges object values into the base configuration, replaces scalar or array values, and cannot override the schema version, adopted SVC version, or any non-`dev` field. The effective result must pass the same strict schema.

Use `svc dev identity --repo <repo> --json` to inspect the resolved workspace identity. Use `svc dev status [target] --repo <repo> --json` only to observe declared targets: it never starts or takes over a process. Use `svc dev ensure <target> --repo <repo> --json` to handle exactly one declared target. Ensure reuses a healthy endpoint, refuses an occupied but unhealthy endpoint, and reports the required consumer action for a manual provisioner. It coordinates executable provisioning only at the declared scope and relinquishes process authority after readiness succeeds.

Worktree scope is the default and a worktree-scoped probe endpoint must prove the resolved instance; repository scope intentionally shares a capability, and host scope requires an explicit `host_key`. Only `${dev.instance}`, `${dev.worktree.id}`, `${dev.profile}`, and `${dev.target}` interpolate in declared dev values. Commands are argument arrays without a shell, and configured working directories must stay inside the workspace.

## Add Optional Editor or Package Bridges

Use `svc dev setup vscode [target] --repo <repo> --plan --json` or `svc dev setup npm [target] --repo <repo> --plan --json` to inspect one bounded bridge. Apply only its exact current digest with `--apply <digest>`. Setup owns only marked VS Code Tasks and exact reserved root package scripts that call `svc dev ensure <target>`; it never reads `launch.json`, chooses a package manager, creates package metadata, removes orphan entries, or overwrites a Consumer conflict.

## Upgrade Deliberately

`svc self-update` plans an update of the installed executable only. It never adopts guidance for this project. After an update, inspect `svc status`, look up the release migration guidance, apply necessary consumer-owned changes under this repository's mutation gate, then run `svc adopt <installed-version>` and explicitly apply its plan.

## Work With the Project, Not Around It

Read root and local `AGENTS.md` instructions before editing governed files. Keep active reasoning in the project's task packet. Use SVC as an on-demand upstream authority; do not create copied SVC protocol documents, a hidden SVC state directory, or an independent task tracker.
<!-- svc:generated skill sha256=eb3dc397d1d33129683fa4313a2de28951c980a229a9a69a10bca896b4e7575c -->
