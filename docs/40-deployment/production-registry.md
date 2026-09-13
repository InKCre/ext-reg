# 生产 Registry 与 PostgreSQL 切换

公开 origin 保持 `https://registry.inkcre.dev`。迁移目标是一个运行于 Heroku Eco dyno 的 CPython / FastAPI 服务容器、Registry 专属 Neon PostgreSQL 项目和既有私有 R2 桶。代码实现不等于生产切换；旧生产仍由 Worker 与 D1 服务，直至获得明确生产授权并完成以下步骤。当前资源身份、演练结果及切换状态记录在活动 task packet。

`production.yml` 只接受精确 current-main SHA。`verify` 执行仓库检查和容器构建，不修改远程资源。`deploy` 在受保护 production 环境中，重新核验 main 后对已配置 app 向前迁移、配置数据库和单桶 S3 凭据、发布同一镜像，并验证 Heroku app origin。它不自动导入 D1、不改变域名、不创建示例数据，也不删除旧资源。

production 环境需要 `HEROKU_APP_NAME`、`S3_ENDPOINT_URL`、`S3_BUCKET` variables，以及 `HEROKU_API_KEY`、`MIGRATION_DATABASE_URL`、`DATABASE_URL`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY` secrets。首次配置保持既有 R2 桶，S3 token 仅授予该桶的对象读写。`MIGRATION_DATABASE_URL` 使用 `registry_owner`，仅交给迁移容器与可信角色配置命令；`DATABASE_URL` 使用同一数据库的普通 `registry_app` 角色和独立密码。迁移创建该角色及业务表授权，控制器设置密码后以 `web=1:eco` 启动应用。owner 连接与平台控制 token 不进入运行服务配置。数据库连接属于独立 Registry 项目，不复用 core-py 的数据库或发布生命周期。

## 首次切换

1. 明确来源 D1、目标 PostgreSQL、R2 桶、Heroku app、公开路由和获准变更窗口。先验证空库迁移、快照导入及整个发布流程；保存旧 Worker 版本与现有路由配置。
2. 暂停旧入口的发布写入并等待在途请求结束。停止 Web、Toolkit、CI publisher 等所有写入来源；只读分发可以继续。不要在旧入口仍接收写入时进行最终导入，也不要引入临时双写。
3. 使用 Wrangler 的 `d1 export <database> --remote --output <private-snapshot.sql>` 保存最终快照。来源 ID 显式传入，不从已删除的 Worker 配置猜测。限制快照文件权限；它包含凭据哈希和私有元数据。用 SQLite 将这份受信任导出转换成临时 SQLite 文件，执行完整性与外键检查。原始 token 从不进入快照。
4. 对空目标运行 `pnpm db:migrate`，然后运行 `pdm run python -m inkcre_extension_registry.import_d1 <snapshot.sqlite>`。导入器拒绝非空目标，在同一事务中转换内部 ID 并核验每张表全部逻辑字段的规范化内容摘要；任何失败回滚全部导入。旧时间戳、空值、JSON、凭据哈希、release 状态及 R2 key 都参与比较。
5. 再运行同一命令并加 `--verify-only`。保存仅含行数和摘要的报告；抽查既有 wheel、Core Metadata、MF manifest / assets 的实际 R2 内容与公开身份。导入不移动、重写或公开 R2 对象。旧 `migrations/` 是来源 schema 历史，包内 Tortoise 迁移是新库 schema 历史。
6. 启动已验证镜像，先通过 app origin 验证只读目录、详情、私有认证和原生协议。将 `registry.inkcre.dev` 指向新服务并配置证书，验证缓存、ETag、GET / HEAD、Simple 内容协商及下载。确认旧 Worker 不再接收发布写入后，恢复新服务的发布能力。
7. 保存最终来源快照、导入摘要、镜像 revision、数据库迁移位置及路由验收。旧 D1 / Worker 的删除须在约定保留窗口后另行执行，不能以 PR 合并代替资源删除授权。

## 故障恢复

切流前任何失败都维持旧入口的写入暂停，调查目标库和对象状态后重试；如果取消切换，可恢复旧入口写入。导入器不会清空已有目标，失败后只有在确认它是本次专属迁移目标时才能重建。

新库尚未接受写入时，可以恢复旧路由与旧 Worker。新库已经接受写入后，旧 D1 不再完整；此时先停止新写入并保全两侧数据，通过修复新服务或经核验的数据合并恢复。直接回退旧 Worker 不能声称无损恢复。

PostgreSQL 事务不覆盖 R2。中断上传可能留下不可达 staging 对象；公开可见性仍由数据库关联和 release 状态决定。后续修复追加迁移，不回写已部署历史，也不使用 `--fake` 掩盖 schema 与迁移记录不一致。
