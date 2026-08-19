# Implementation Result — Runtime alignment

- **Status:** local implementation complete; released-lock normalization blocked on publication
- **Authority:** active implementation plan plus the latest authorized batch
- **Supersedes:** none
- **Evidence:** repository checks and Peer adoption checks recorded below

## Batch 1 — Contract and Toolkit

- Registry Pydantic models generate checked OpenAPI/JSON Schema.
- datamodel-code-generator and Hey API generate Python and Web consumers; the
  generator formats its own output and `contracts:check` compares regeneration.
- Toolkit 0.2.0 finalizes an existing PEP 517 wheel with the versioned
  `inkcre-extension.json` installed record, then inspects the repacked wheel.
- Project/entry-point grammar is carried in generated schemas; Packaging and
  semantic-version handle native name/version/range semantics that JSON Schema
  cannot express.

## Batch 2 — Core Python Runtime and Core adoption

- `inkcre-extension-runtime-core-py 0.1.0` owns Manager/Base, exact Release
  resolution, local-first installed discovery, pip closure acquisition, module
  loading and Core-specific contribution publication/rollback.
- Core restored `ExtensionModel` as the rich Active Record and removed the
  Store/Repository and embedded Runtime/Distribution duplicates.
- Local integration used the built Runtime wheel/editable source only; no
  `file:`/path dependency was written to Core manifests.
- Before the explicitly authorized test removal, Core integration evidence was
  474 passed/41 skipped, including Distribution 25 passed. Those tests and
  their dependencies are now deleted; current gates are PDM lock, format,
  lint, type-check, migration heads and seven first-party wheel
  build/finalize/verify operations.

## Batch 3 — Client Web Runtime and Client adoption

- `@inkcre/extension-runtime-client-web 0.1.0` owns the concrete rich-model
  manager, native Release reader and Module Federation lifecycle.
- Client removed its embedded Runtime/reader/state Port, retaining Peer
  delegation, Registry-origin policy, setup projection and popup UI.
- Local integration used a packed tarball only; no local/path/workspace Runtime
  dependency remains in Client manifests.
- Before the explicitly authorized test removal, Client integration evidence
  was 122 tests plus all builds. Those tests and their runners are now deleted;
  current gates are format, lint, type-check, workspace/database/runtime
  contract generation and Chrome/Firefox/Web/extension builds.

## Integration and review

- ext-reg now has no test tree or test runner. Its current `pnpm check` passes
  contract regeneration, format, lint, Python/Web type-check, all Registry,
  Toolkit and Runtime builds, and Worker dry build.
- Both Runtimes now reject a Registry URL with a path instead of silently
  discarding it. Python retains restart-required after pip mutation begins;
  this intentionally rejects the review suggestion to retry a possibly
  partially mutated interpreter.
- Core CI and first-party publication now finalize raw PEP 517 wheels before
  verify/publish. Workflow lint and diff check pass.
- `.github/workflows/packages-release.yml` prepares three independent,
  manually selected package releases without coupling them to Registry service
  deployment. YAML and actionlint pass; all three package assets build locally.
- Python development is rooted at one PDM workspace and one `pdm.lock`;
  `uv.lock`, uv commands and nested Runtime environments were removed. The
  Cloudflare-produced `pylock.toml` remains a Worker packaging input;
  pywrangler's internal resolver is not a repository development interface.
- All repository, Runtime and Peer tests were explicitly deleted, including
  pytest/Vitest/Playwright dependencies, scripts, fixtures and CI test jobs.

## Remaining gate

- No commit, push, release, package publication, deployment or merge occurred.
- Publish Toolkit 0.2.0, Python Runtime 0.1.0 and Web Runtime 0.1.0 only after
  separate authorization; then update Core PDM and Client pnpm released locks
  and rerun their frozen full checks.

Do not append investigation narrative or restate historical product decisions.
