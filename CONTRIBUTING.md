# Contributing

Use Python 3.13, PDM 2.28, Node 22, and pnpm 11.11.0. The Registry, Toolkit,
and Python Runtime use PDM's workspace support. Install frozen
dependencies and run the repository contract before opening a pull request:

Verification follows the organization-wide
[Verification and Test Policy](https://github.com/InKCre/.github/blob/main/TESTING.md). The commands below are this
repository's admitted local evidence.

```bash
python -m pip install -r requirements-pdm.txt
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
pnpm check
```

本地、CI 与服务镜像都通过 `requirements-pdm.txt` 安装兼容的 PDM 及其依赖。
运行 PDM 前应先执行这条安装命令，因为项目锁文件不会约束 PDM 自身的下载客户端。

Shared InKCre product truth and cross-unit contracts are mounted read-only from
`InKCre/docs`. Initialize the pinned reference after cloning:

```bash
git submodule update --init --recursive docs/_shared
```

Do not edit `docs/_shared/**` from this repository. The repo-root
`.agents/skills/edit-svc-shared-docs` wrapper points coding Agents to the
canonical Hub-first edit and isolated ref-bump workflow.

`pnpm check` verifies generated contracts, formatting, lint, types,
the Registry packages, Web Runtime build, and real PostgreSQL / S3 HTTP acceptance.
The database checks require an isolated disposable PostgreSQL instance; see
[local development](docs/40-deployment/local-development.md). To update an executable
contract intentionally:

```bash
pnpm contracts:generate
pnpm check
```

Pull requests target protected `main`, preserve linear history, and include the
scope, verification evidence, risk, and rollback. CI and previews may publish
ephemeral evidence, but canonical packages and production deployment only come
from an exact successful current-`main` revision. Do not commit credentials,
local Wrangler state, generated dependency directories, or unrelated changes.

Package release intent uses the ecosystem-native release tool:

- Registry, Toolkit and Core Python Runtime changes use Towncrier. Create one
  fragment in the changed project's `.changes/` directory, for example
  `pdm run towncrier create --config towncrier.toml --dir toolkit 123.added.md`.
  The root `.changes/` belongs to the Registry service; `toolkit/.changes/` and
  `runtimes/core-py/.changes/` belong to those independently versioned packages.
- Client Web Runtime changes use `pnpm changeset`. Changesets creates the
  protected-main Version PR and updates its version and changelog.

The four versions are independent. A Python Version PR consumes pending
Towncrier fragments and updates only versions, changelogs and the workspace
lock. The Web Version PR consumes Changesets. Registry production deployment
remains separate from package publication even though the service has its own
version and changelog.

Every protected-main update reconciles both kinds of Version PR and publishes
prepared package versions. Python packages with pending fragments wait for the
Python Version PR instead of silently treating an existing tag as successful
publication. Existing releases are left unchanged.

Generated Version PR branches are checked through an explicit workflow dispatch.
GitHub deliberately prevents ordinary `GITHUB_TOKEN` pushes from recursively
starting `pull_request` workflows; the dispatch attaches the normal required
check to the generated head commit without bypassing branch protection.

Package publication runs static and generated-contract checks, then builds its
own release assets. The Registry database journey remains in repository CI; it
is not a dependency of Toolkit or Runtime publication.

Registry, Toolkit publication, Runtime publication and Registry production changes are separate
privileged operations. Extension publishers install the independent
`inkcre-extension-toolkit[cli]` distribution, prepare typed associations with
`inkcre-ext prepare-release`, use PDM/Twine for wheels or
`inkcre-ext upload-module-federation` for a native Remote snapshot, and publish
the Release explicitly. Source revision and build identity should accompany the
prepare request.

格式与 lint 覆盖正式维护的源码、测试和脚本；`tasks/`、外部维护的 `.agents/` 及共享文档挂载不按本仓库规则重写。Ruff 的范围由 `pyproject.toml` 拥有，Prettier 的范围由 `.prettierignore` 拥有。任务实验若成为正式验证或交付步骤，应迁入 `scripts/` 或 `tests/`。本地与 CI 都执行 `pnpm check`，修复格式另用 `pnpm format`。

局部反馈有稳定入口，完整验收仍由 `pnpm check` 负责：

- `pnpm protocols:check`：固定文档候选身份/重试与原生合同向量，不启动 Registry、PostgreSQL 或 S3。
- `pnpm artifacts:check`：对象容量组、取消和冲突传播，不访问对象存储。
- `pdm run python scripts/check_packages.py --only delivery`（或 `release`、`native`、`preview`）：选择既有独立检查；发布协调夹具使用受控 Git 历史，但执行当前工作树的发布脚本。
- `pdm run python runtimes/core-py/check_lifecycle.py`：从工作树快速检查 Host 生命周期；构建 Core-Py wheel 后 `pnpm core-py:check` 从隔离安装的 wheel 验证相同合同。
- `pnpm packages:check`：以上包职责及 Registry/Toolkit/Core-Py 独立安装见证；`pnpm registry:check` 保留真实一次性 PostgreSQL/Moto/HTTP 旅程。

Registry 现在要求 Toolkit >=0.5.1，因为服务复用其冻结文档指纹函数。协调版本准备只消费一次 Toolkit 的发布意图，不授权发布；独立安装 Registry 前须先让该 Toolkit 版本的 wheel 可供安装；服务镜像则从同一精确源码非 editable 安装配套版本。不能使用旧 0.5.0 替代或依赖源码工作区遮蔽缺失函数。独立包发行工作流在生成资产后验证 Core-Py wheel，仍不依赖 Registry 数据库。
