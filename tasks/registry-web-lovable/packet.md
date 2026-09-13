# Registry Web：产品完善与 Python / PostgreSQL 迁移

## 目标与当前状态

完成 Registry 的 minimum lovable product：目录、扩展详情和 Publisher 对齐 client-web，复用 design 的公开样式包；由一个 Python 服务交付 Web、API 和静态资源。服务从 Python Workers / D1 迁到常规 CPython / Neon PostgreSQL，保留 R2 与公开协议，减少特殊运行时适配和两套数据库技术的维护成本。

**2026-09-13，Sir 已确认完整方案与相应调整，授权继续 preview，并明确要求 Heroku Eco。** 单一 CPython 服务、普通数据库角色、文件重验证及浏览器就绪修复已交付。完整 CI、真实 Eco / Neon / R2 协议、浏览器与重部署保留数据验收已通过；临时验收资源已清理。生产尚未切换。

本 packet 是父任务唯一的工作控制入口，保存目标、决策、执行位置和证据边界，不拥有长期架构事实，也不代替 Sir 的验收。[计划](plan.md)拥有推进顺序；[证据](evidence.md)区分当前结果、旧 Worker 基线与待验证事项。父任务关闭前保留整个 packet。

## 决策、当前实现与授权

| 对象 | From → To | 不变量 |
| --- | --- | --- |
| 运行时 | Python Worker → CPython / FastAPI / Jinja 单一容器，Heroku Eco dyno | Web、API、分发与静态资源同一应用，无独立前端部署 |
| 持久化 | D1 / SQLAlchemy Core → Neon PostgreSQL / Tortoise ORM / asyncpg | 业务唯一身份、namespace 边界、发布状态及不可变关联保持兼容 |
| 关系与迁移 | 复合主键 → Release、Distribution、File 内部主键与普通外键，业务身份用唯一约束保持 | 内部 ID 不进入公开契约；旧 D1 历史不改写，新迁移仅向前执行 |
| 文件存储 | R2 binding → boto3 S3 SDK | 原有 key、文件身份、流式读取与先 staging 后可见的语义保持 |
| 预览 | 独立 Heroku Eco app / Neon branch / 私有 R2 bucket | 更新保留数据，不生成示例扩展，不复制生产业务数据 |
| 产品 | 保留已接受的简洁目录、详情与 Publisher，复用 design | 无 hero、额外教程面板、错误 logo 或环境驱动的产品分支 |

此前“恢复原始 SQL”不再是当前路线。Tortoise 使用独立关联主键，避免库对外键兼主键的加载限制；没有自建驱动、查询语言或事务模拟。R2 与 PostgreSQL 不组成分布式事务。导入在一次数据库事务中转换关系，并比较全部逻辑内容摘要，不能只比较行数。

实现、验证、提交、推送和 PR 更新沿用明确授权，不重复请求。生产资源变更与切流仍需仓库 [AGENTS.md](../../AGENTS.md) 所要求的单独明确授权；合并也不包含在当前交付授权内。到达生产步骤前先完成可审阅的迁移演练和精确切换方案。

## 归属与范围

持久化和发布设计归 `docs/30-unit-tdd/registry-control-plane.md`；Web 与 design 消费归 `registry-web.md`；运行、迁移、交付和恢复归 `docs/40-deployment/`。源码、模型、迁移、配置与 CI 拥有可执行事实。Registry、Toolkit、Host SDK 与 first-party Extensions 保持独立发布；不修改 core-py 业务数据或合并其发布周期。

配套 `.github` PR #32 中的 Worker / D1 假设随实现更新。未直接修改 Spoke 的 `docs/_shared/`；本次内部运行时与部署细节由 Registry Unit 文档及组织交付约定承担。

## 执行位置与下一步

当前在计划 03 的交付收尾；[PR 33 预览](https://inkcre-ext-reg-pr-33-02f4786fe565.herokuapp.com) 已运行单个 Eco dyno。功能验收提交为 `a86549309726c713f1ea10e6f6636c42ffcddeff`；后续证据提交只更新文档和截图，发布后以 `/livez` 核对最终 PR head。完整结果和截图见[证据](evidence.md)。

应用使用普通 `registry_app`，owner 仅用于交付迁移；文件每次先检查 release 状态，再依据 ETag 返回内容或 304。真实浏览器暴露的脚本就绪竞态也已修复：Connect、复制 ID 和主题按钮等待事件处理器；凭据输入没有原生表单字段名。已轮换验收中使用过的 PR 凭据，旧凭据被拒绝。

GitHub preview 的 Heroku、Cloudflare、Neon 与 reviewer 凭据及变量均已配置。Cloudflare 控制 token 只有当前账户的 R2 存储与账户 token 管理权限；应用只拿所属桶的对象 token。主工作流的可信控制器尚未合入默认分支，本次通过本机执行仓库同一 Dockerfile 和控制器完成 pre-merge 验收，没有增加产品交付流程。

Registry Neon 项目为 `wandering-base-13707928`。根分支 `br-muddy-term-aw4iive7` 保持空库，无 compute 的空基础分支为 `br-polished-mode-awi5dixy`；PR 33 使用 `br-falling-breeze-awj9y9ao`。PR 只登记 reviewer namespace 和凭据，没有扩展、版本或文件。临时远程验收 app / bucket `inkcre-ext-reg-qa-33`、Neon `br-plain-wildflower-awu0s6yy` 和迁移检查分支 `br-dry-meadow-awo759yq` 已删除并确认不存在。

下一阶段是单独获准的生产切换：核验真实来源、停止旧写入、导入并核对最终快照、切换公开路由。操作及恢复条件已在 `production-registry.md` 准备好。未合并 PR，也未修改生产 D1 / R2 / Worker / 公开域名；父任务保留到生产行为与最终验收完成，不能因 preview 通过便关闭 packet。

## 工作坐标

- Registry 工作树：`/Volumes/WorkSSD/Development/InKCre/.worktrees/registry-web/ext-reg`；分支 `feat/registry-web-lovable`；[PR #33](https://github.com/InKCre/ext-reg/pull/33)。
- [旧 Worker 预览](https://inkcre-ext-reg-pr-33.lanzhijiang.workers.dev/)仍代表 `03de36b`，不是本次 CPython 迁移的验收地址。
- 治理工作树：`/Volumes/WorkSSD/Development/InKCre/.worktrees/registry-web/governance`；分支 `feat/registry-worker-preview`；[PR #32](https://github.com/InKCre/.github/pull/32)。
