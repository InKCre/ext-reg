# Core 数据库迁移所需的 Runtime SDK 异步能力

## 父任务与授权

本 packet 仅拥有 ext-reg 的上游 SDK 实现 slice。唯一线性计划由 core-py 的
`tasks/async-database-boundaries/plan.md` 拥有；不得在此建立另一条全量迁移计划。
Sir 已授权修改 ext-reg、提交、推送与创建 PR，明确禁止 Agent 合并。

从 origin/main `006759a` 建立独立分支 `feat/runtime-async-persistence`，worktree 为
`/Volumes/WorkSSD/Development/InKCre/.worktrees/ext-reg-async-persistence`。既有 ext-reg checkout 未改动。

## 实现与交付边界

Runtime 0.1.4 为 ExtensionBase 增加配置、状态及启动的 async API，绑定 Host 的 awaitable
持久化能力；旧 API 及现有 SDK ExtensionManager 保留同步合同。一个 publication scope
同时服务两种启动入口，在失败或取消时撤销本次活动资源，阻止未完成时重复启动。

调查确认 Source catalog activation 也调用数据库。异步启动调用新
SourceManager.sync_source_types_async；Core 采用 SDK 时先提供这个 capability，再切换 Host。
SDK 不创建数据库连接、不持有 session、不引入 fallback 或 worker 包装。Host 负责事务和锁。

版本及 changelog 通过 Changie 生成，PDM lock 只将本地 workspace SDK 版本由原有陈旧的
0.1.2 更新为 0.1.4。Registry 服务、shared contracts、web runtime 和 Toolkit 源码未变。

`.github/workflows/packages-release.yml` 仅在 main 发布正式 artifact。Agent 不得合并，故此
slice 完成到可审阅 PR 后，Core 等待外部合并和 0.1.4 artifact；不会用本地 wheel URL 代替正式依赖。
父任务及本 packet 此时保持打开。

## 验证与限度

- Runtime 及仓库 Python lint、format、pyright 通过；pnpm contracts:check、format:check、type-check 通过。
- `pdm build --project runtimes/core-py --dest dist/runtime-core-py` 成功构建 wheel/sdist。
- `pdm run python tasks/async-runtime-persistence/probe.py` 通过；另将构建的 wheel 正常安装到独立
  Python 3.12 环境，使用 Core 当前 FastAPI 0.139.2 执行同一 probe，也通过。源码环境为 Python 3.13。
- probe 是本任务的 public SDK boundary 实验，不是新常驻 CI suite。它使用真实 FastAPI/HTTP transport，
  用内存 Host adapter 隔离持久化 owner，验证 typed mutation、两个启动 await 点的取消、失败撤销、
  重新启动和旧同步启动兼容。它不证明 PostgreSQL 事务；该证据仍由 Core 的真实数据库验收拥有。
- 本机 Node 为 26，pnpm 对项目要求的 Node 22 给出警告；上述 JS 检查通过。正式 CI 使用 Node 22。
- 本机没有执行 Registry 的 PostgreSQL 全量 gate，SDK 变更未触及该数据库；仓库 CI 使用一次性 PostgreSQL
  执行完整 pnpm check。不能把本地 package checks 写成全仓集成通过。

## 已复现的既有问题

当前 FastAPI include_router 会在 app.routes 中保存 _IncludedRouter，而旧 SDK 的 PublicHTTPRouteClaim
只检查顶层 route.path。单独使用已安装 SDK 0.1.3 + FastAPI 0.139.2 的旧 on_start 已复现
`Public Extension routes were not published: [('GET', '/probe/callback')]`。因此 probe 的成功启动不声明
public callback；本次覆盖 routes/inbounds 的取消撤销，没有伪造 public-claim 成功证据。该问题不由
数据库异步化引入，未扩展本次源码范围；采用方的 callback 验收仍受其影响。
