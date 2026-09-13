# Registry Web：产品完善与 Python / PostgreSQL 迁移

## 目标与当前状态

完成 Registry 的 minimum lovable product：目录、扩展详情和 Publisher 对齐 client-web，复用 design 的公开样式包；由一个 Python 服务交付 Web、API 和静态资源。服务从 Python Workers / D1 迁到常规 CPython / Neon PostgreSQL，保留 R2 与公开协议，减少特殊运行时适配和两套数据库技术的维护成本。

**2026-09-13，Sir 在确认方向、要求先更新 packet 后，明确授权“开始实施”，并允许通过 Neon CLI 创建项目和数据库分支。** CPython / FastAPI / Jinja、Tortoise / asyncpg、boto3 和单一 OCI 服务已实现。真实 Neon 上的发布流程、D1 导入保真和完整 `pnpm check` 已通过；容器 CI 的提交结果由 PR checks 记录，远程预览仍待凭据恢复，生产尚未切换。

本 packet 是父任务唯一的工作控制入口，保存目标、决策、执行位置和证据边界，不拥有长期架构事实，也不代替 Sir 的验收。[计划](plan.md)拥有推进顺序；[证据](evidence.md)区分当前结果、旧 Worker 基线与待验证事项。父任务关闭前保留整个 packet。

## 决策、当前实现与授权

| 对象 | From → To | 不变量 |
| --- | --- | --- |
| 运行时 | Python Worker → CPython / FastAPI / Jinja 单一容器；Heroku 是当前部署实现，托管平台选择待确认 | Web、API、分发与静态资源同一应用，无独立前端部署 |
| 持久化 | D1 / SQLAlchemy Core → Neon PostgreSQL / Tortoise ORM / asyncpg | 业务唯一身份、namespace 边界、发布状态及不可变关联保持兼容 |
| 关系与迁移 | 复合主键 → Release、Distribution、File 内部主键与普通外键，业务身份用唯一约束保持 | 内部 ID 不进入公开契约；旧 D1 历史不改写，新迁移仅向前执行 |
| 文件存储 | R2 binding → boto3 S3 SDK | 原有 key、文件身份、流式读取与先 staging 后可见的语义保持 |
| 预览 | 当前实现为独立 Heroku app / Neon branch / R2 bucket；尚未部署，托管平台可单独调整 | 更新保留数据，不生成示例扩展，不复制生产业务数据 |
| 产品 | 保留已接受的简洁目录、详情与 Publisher，复用 design | 无 hero、额外教程面板、错误 logo 或环境驱动的产品分支 |

此前“恢复原始 SQL”不再是当前路线。Tortoise 使用独立关联主键，避免库对外键兼主键的加载限制；没有自建驱动、查询语言或事务模拟。R2 与 PostgreSQL 不组成分布式事务。导入在一次数据库事务中转换关系，并比较全部逻辑内容摘要，不能只比较行数。

实现、验证、提交、推送和 PR 更新沿用明确授权，不重复请求。生产资源变更与切流仍需仓库 [AGENTS.md](../../AGENTS.md) 所要求的单独明确授权；合并也不包含在当前交付授权内。到达生产步骤前先完成可审阅的迁移演练和精确切换方案。

## 归属与范围

持久化和发布设计归 `docs/30-unit-tdd/registry-control-plane.md`；Web 与 design 消费归 `registry-web.md`；运行、迁移、交付和恢复归 `docs/40-deployment/`。源码、模型、迁移、配置与 CI 拥有可执行事实。Registry、Toolkit、Host SDK 与 first-party Extensions 保持独立发布；不修改 core-py 业务数据或合并其发布周期。

配套 `.github` PR #32 中的 Worker / D1 假设随实现更新。未直接修改 Spoke 的 `docs/_shared/`；本次内部运行时与部署细节由 Registry Unit 文档及组织交付约定承担。

## 执行位置与下一步

当前在计划 03：`4d79874` 的完整 CI、镜像构建与 HTTP 启动检查已通过；一次性 Neon 分支上的本地 Chromium 验收也已通过，覆盖双版本 Web 发布、详情、撤回恢复、搜索与移动端，见[证据](evidence.md)。Sir 询问 Heroku 的必要性后，已澄清它只是当前应用托管选择，并非 Neon / ORM 的必要依赖；“继续预览验收”不自动确认替换托管平台。已请求在沿用当前 Heroku 实现与先评估 Cloudflare Containers 之间明确选择。

2026-09-13 重新检查时，本机 Heroku 登录仍失效，GitHub preview 缺 `HEROKU_API_KEY` 和 `CLOUDFLARE_PREVIEW_API_TOKEN`。Neon 的项目范围 API key、preview variables 和 Cloudflare 账户 ID 已配置，密钥未进入源码或 packet。当前没有新 CPython 远程预览地址；托管平台与所需凭据明确后才能完成远程验收。

Registry 专属 Neon 项目为 `wandering-base-13707928`，PostgreSQL 17、aws-us-east-1、database `registry`。根分支 `br-muddy-term-aw4iive7` 保持空库，未导入生产数据；无 compute 的空基础分支为 `br-polished-mode-awi5dixy`。PR 33 分支为 `br-falling-breeze-awj9y9ao`，一次性验证分支为 `br-dry-meadow-awo759yq`，后两者到期日为 2026-09-20。后续 PR 从空基础分支建库并运行提交中的迁移，避免把生产数据引入预览。

完成实现交付需要同一提交的完整检查、镜像、真实远程预览和产品 / 协议验收证据。缺少远程验收时不能写作“实现已验收”。生产迁移另需真实来源核验、公开域名验收与旧写入停止证据；不能因代码或 PR 完成便关闭父任务。

## 工作坐标

- Registry 工作树：`/Volumes/WorkSSD/Development/InKCre/.worktrees/registry-web/ext-reg`；分支 `feat/registry-web-lovable`；[PR #33](https://github.com/InKCre/ext-reg/pull/33)。
- [旧 Worker 预览](https://inkcre-ext-reg-pr-33.lanzhijiang.workers.dev/)仍代表 `03de36b`，不是本次 CPython 迁移的验收地址。
- 治理工作树：`/Volumes/WorkSSD/Development/InKCre/.worktrees/registry-web/governance`；分支 `feat/registry-worker-preview`；[PR #32](https://github.com/InKCre/.github/pull/32)。
