# 现有证据与迁移验证

本文件属于 [Registry 父任务](packet.md)，拥有跨实现阶段的证据和适用范围。Worker / D1 部分是实施前历史基线；CPython / PostgreSQL 的当前结果见文末实施记录。生产切换仍无完成证据。

## Worker / D1 基线

Registry 分支为 `feat/registry-web-lovable`，实施前提交 `03de36b`，最初基线为 `422a6cb`。开始实施前只有 packet 调查记录未提交。

已交付的 Web 对齐 client-web：实际几何 logo、普通字号、直角边框与紧凑布局，复用 design 已有公开 Sass package。目录有搜索和发布者筛选；详情有精确版本及原生分发；Publisher 支持准备、上传、发布、撤回、恢复及私有分页。环境信息不塑造产品页面、控件和 URL。

现有 PR 预览是完整 Python Worker，配套独立 D1 / R2。部署保留数据，关闭时按 PR 清理资源。发布代码与可信部署控制器分开处理；源提交检查、凭据隔离和清理边界是需要保留的交付结果，Worker 具体机制不是新运行时必须继承的方案。

### Demo 清理结果

已移除部署时创建示例 Release 的代码，以及样例详情 / manifest 专用检查；删除 66 行，没有增加产品机制。PR #33 预览中已清理 `demo/github` 的 `1.0.0`、`1.10.0`、`2.0.0-rc.1`，以及 `demo/memos`、`demo/rss`、`demo/notes` 各 `1.0.0`，合计 4 个扩展、6 个版本、12 个精确 R2 对象。

清理前核对 source repository / revision、snapshot hash 与 asset paths；未重置数据库。D1 UUID `7d67ae5e-c0b3-4fca-841c-4c4c7661dd73` 保持不变，namespace、凭据和迁移记录数保持不变，外键检查通过。旧 demo 详情返回 404，空目录与 Publisher 登录、空 release 列表已验证。该结论只适用于当时的预览状态，不能据此假定生产为空。

### SQLAlchemy Core 交付结果

当时的 `service/database.py` 和 `service/repository.py` 使用 SQLAlchemy Core 表定义、查询表达式及 SQLite 编译器；D1 binding 执行编译出的 SQL 和绑定参数，原生 `batch()` 保持关联创建的原子性。没有 ORM Session、关系加载或实体变更跟踪。

此前替换了 Repository 的 27 处 SQL 及预览凭据维护 SQL。SQLAlchemy 2.0.52 的 pure-Python wheel 在当前 Pyodide Worker 中运行，PDM 与 Worker lock 对齐。已检查的 `sqlalchemy-cloudflare-d1` 0.3.11 使用同步 `run_sync`，Worker 路径的 commit / rollback 为空操作；这是当时没有接入其 ORM 事务的原因，不是对全部 D1 工具的普遍结论。

`scripts/check_registry.py` 使用一次性本地真实 Worker / D1 / R2，验证完整发布、幂等、私有分页、namespace 范围及关联写入故障后扩展和版本一同回滚，已纳入 `pnpm check`。完整检查曾通过，具体最终 CI / 部署证据见 [ext-reg PR #33](https://github.com/InKCre/ext-reg/pull/33)。这些断言中的业务不变量需迁到真实 PostgreSQL 上重新证明。

### 旧预览交付状态

历史预览地址为 `https://inkcre-ext-reg-pr-33.lanzhijiang.workers.dev/`。最近的代码更新保留既有 D1 / R2 和 Publisher 凭据，没有初始化凭据或上传验收数据。

旧流程中 GitHub preview 环境已配置 `REGISTRY_PREVIEW_PUBLISHER_TOKEN`，`CLOUDFLARE_PREVIEW_API_TOKEN` 尚未配置；远程预览由本机 Wrangler 登录执行同一控制器更新。控制器进入 main 后才能自动触发，但本任务尚未合并或修改生产资源。迁移方向已改变，不应为了旧流程而默认补齐这个前置条件。

配套 [.github PR #32](https://github.com/InKCre/.github/pull/32) 基于 Worker 预览编写；其适用内容须在交付方案中重新审阅。本记录不宣布该 PR 自动作废，也不代替修改或关闭它的实际操作。

## 选型与复用依据

已核对现有 D1 schema：`releases`、两类 distribution 和 `python_files` 使用多列身份及复合外键。这是 ORM 比较必须覆盖的实际关系；可以提出代理主键方案，但必须保留业务唯一性和对外身份，不能为了通过库限制而静默弱化约束。

当前候选调查发现：Tortoise 1.x 已有内置迁移，但仅支持单列主键；Peewee 4.x 已有异步扩展和迁移生成，指向复合主键的外键仍受限；Django 6.0 的普通 ForeignKey 仍不能引用复合主键模型；Edgy 对复合主键与外键组合仍有成熟度提醒。SQLModel、Ormar、Edgy 基于 SQLAlchemy，API 风格不同不等于底层驱动独立。Piccolo 对当前关系的完整支持尚未确认。调查时尚没有候选在本项目完成过 ORM 实现验收。

来源：[Tortoise 模型](https://tortoise.github.io/models.html)与[迁移](https://tortoise.github.io/migration.html)、[Peewee 模型](https://docs.peewee-orm.com/en/latest/peewee/models.html)与[异步](https://docs.peewee-orm.com/en/latest/peewee/asyncio.html)、[Django 复合主键](https://docs.djangoproject.com/en/6.0/topics/composite-primary-key/)、[Edgy 模型](https://edgy.dymmond.com/models/)、[Piccolo](https://github.com/piccolo-orm/piccolo)。后续选型时复核最终采用版本，不将这些调查冻结为长期事实。

core-py 的 `app/engine.py`、`docs/40-deployment/neon.md` 和 `heroku.md` 已核对：当前使用 SQLModel / SQLAlchemy 与 psycopg，常规 Python OCI 镜像在 Heroku 上运行，Neon 已有连接池、迁移及隔离预览经验。其当前预览从去除应用数据的 `preview-base` 创建 PR 分支；这仅是复用依据，不自动成为 Registry 的新要求。core-py 源码和资源未变更。

Cloudflare 的 PostgreSQL 接入主要展示 JavaScript 驱动；仅换 Neon 不证明 Python Worker 的 ORM 驱动可用。官方 Django / D1 后端注明 `transaction.atomic` 不生效。因此已确认将常规 CPython 一并纳入迁移。R2 可通过标准 S3 SDK 使用，但本项目仍需验证现有对象访问与返回语义。

来源：[Cloudflare PostgreSQL](https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/)、[Python 包](https://developers.cloudflare.com/workers/languages/python/packages/)、[Django 后端事务](https://developers.cloudflare.com/workers/languages/python/packages/django/)、[R2 boto3](https://developers.cloudflare.com/r2/examples/aws/boto3/)。

## 尚待获得的证据

| 主张 | 当前证据边界 | 应在哪一步获得 |
| --- | --- | --- |
| ORM 关系、事务和迁移 | Tortoise 在真实 Neon 的发布验收已通过 | 最终 CI 持续验证 |
| CPython 单一产物 | 实现和本地行为已验证，镜像与远程预览待验收 | 02 CI 镜像、03 远程预览 |
| D1 导入保真 | 一次性 SQLite → Neon 演练已通过，真实生产来源尚未核验 | 04 最终来源核验 |
| 新预览隔离、更新保留数据、无部署 demo | 新控制器已实现，尚未获得远程生命周期证据 | 03 预览生命周期验证 |
| 公开协议、视觉、权限和失败语义保持 | Worker 基线已有部分证据，新实现须重验 | 02 行为检查、03 浏览器与协议验收 |
| 生产已使用 Neon，旧写入路径已停止 | 没有生产变更或切换证据 | 04 获准切流及观察 |

后续每次更新记录具体提交 / 产物、目标环境、执行结果及剩余事项。生产数据、原始凭据、数据库连接串与导出文件不得写入 packet、Git 或测试日志。

## 2026-09-13 CPython / PostgreSQL 实施

- `pnpm registry:check` 已在 Neon 一次性分支 `br-dry-meadow-awo759yq` 通过完整发布流程。使用 Tortoise 实际迁移、真实 PostgreSQL 事务、FastAPI ASGI 请求以及本地 Moto S3 服务；覆盖 Python / MF 上传与重试、发布、撤回恢复、关联失败回滚、并发关联冲突、分页、namespace / blocked 边界、原始文件与 GET / HEAD。
- D1 导入验收已单独通过：临时 SQLite 使用原始 `0001_registry.sql`，包含全部七张表和四种 release 状态。导入后全部字段的规范化摘要一致，包含凭据哈希、空值、JSON、时间戳与 R2 key；非空目标拒绝导入。来源为一次性 fixture，不是生产数据。
- 静态类型、Ruff 和公开契约检查已通过；公开 OpenAPI / schema 无变化。最终完整仓库检查与导入失败回滚检查仍在收尾，最终结果以之后记录为准。
- 新建独立 Neon 项目 `wandering-base-13707928`，数据库 `registry`，PostgreSQL 17 / aws-us-east-1。空基础分支 `preview-base` 为 `br-polished-mode-awi5dixy`，无 compute；根分支、PR 33 分支与测试分支见 packet。没有修改 core-py 的项目或数据。
- GitHub preview 已配置 `NEON_API_KEY`（限制于 Registry 项目）、`NEON_PROJECT_ID` 和 `NEON_PREVIEW_PARENT_BRANCH_ID`。该环境已有审阅者 token，但缺少新的 Cloudflare 控制 token 与 Heroku 凭据；本机 Heroku 登录也已失效。已发出所需输入请求，尚未部署 CPython 远程预览。
- 生产 D1、R2、Worker 和 `registry.inkcre.dev` 未变更。旧 Worker 预览不能证明新运行时通过验收。

- 最终验收发现 Tortoise 1.1 初始 CreateModel 忽略 Meta.constraints，PostgreSQL 实际目录中缺少 CHECK。初始迁移尚未提交或部署到预览 / 生产；现已改为 15 个原生 AddConstraint 操作。只重建一次性测试分支的 schema，再从空库执行完整检查；旧 D1 历史、根分支和 PR 分支未变更。

- 最终本地 `pnpm check` 全部通过，使用 Python 3.13 / Node 22.22.3 与 Neon PostgreSQL 17；覆盖实际 CHECK 拒绝非法导入并回滚、S3 元数据对象缺失时拒绝发布、修复后发布成功。公开契约 / runtime 生成绑定无 diff，design 样式比对、格式、静态类型、全部独立包构建通过。SVC 14.0 healthy。
- Registry 项目范围的 Neon key 查询本项目返回 200，查询 core-py 项目返回 404；GitHub 仓库级没有额外 Heroku / R2 secrets 可复用。配套治理提交为 `dafd33c`，已推送并更新 PR #32。容器实际构建 / 启动与 CI 的最终结果以 PR #33 的同提交 checks 为准。

- 原生 `tortoise upgrade` 已成功将初始迁移应用到 PR 33 分支；PostgreSQL 目录确认 15 个 CHECK，namespace / extension / release 均为 0。没有 demo 或审阅者初始化数据；运行时部署待凭据完成。该初始迁移自此冻结，后续只追加。

- `7ea304e` 的 [CI](https://github.com/InKCre/ext-reg/actions/runs/34736306427) 全部通过，包含依赖审查、PostgreSQL 17 行为验收、容器构建与实际 HTTP 启动。后续收尾给健康探测增加镜像内的 revision 校验；新提交的结果以 PR checks 为准。
- PR 33 与一次性测试分支均通过正式 Neon API 完成独立角色密码轮换，控制器的分支查询、操作等待与连接 URI 读取已在真实 API 验证；这些密码不再继承根分支。Heroku / R2 部署仍未验证。
