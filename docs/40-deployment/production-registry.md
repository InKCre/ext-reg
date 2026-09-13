# 生产 Registry 与 PostgreSQL 切换

公开 origin 保持 `https://registry.inkcre.dev`。2026-09-13 起，由一个运行于 Heroku Eco dyno 的 CPython / FastAPI 服务容器、Registry 专属 Neon PostgreSQL 项目和既有私有 R2 桶提供服务。Web、API、静态资源和原生分发由同一镜像交付。旧 Worker / D1 已退出公开路由，保留为本次迁移的恢复依据。

`production.yml` 只接受精确 current-main SHA。`verify` 执行仓库检查和容器构建，不修改远程资源。`deploy` 在受保护 production 环境中，重新核验 main 后对已配置 app 向前迁移、配置数据库和单桶 S3 凭据、发布同一镜像，并验证 Heroku app origin。它不自动导入 D1、不改变域名、不创建示例数据，也不删除旧资源。

production 环境需要 `HEROKU_APP_NAME`、`S3_ENDPOINT_URL`、`S3_BUCKET` variables，以及 `HEROKU_API_KEY`、`MIGRATION_DATABASE_URL`、`DATABASE_URL`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY` secrets。首次配置保持既有 R2 桶，S3 token 仅授予该桶的对象读写。`MIGRATION_DATABASE_URL` 使用 `registry_owner`，仅交给迁移容器与可信角色配置命令；`DATABASE_URL` 使用同一数据库的普通 `registry_app` 角色和独立密码。迁移创建该角色及业务表授权，控制器设置密码后以 `web=1:eco` 启动应用。owner 连接与平台控制 token 不进入运行服务配置。数据库连接属于独立 Registry 项目，不复用 core-py 的数据库或发布生命周期。

Heroku 交付为 Uvicorn 设置 `FORWARDED_ALLOW_IPS=*`，由平台 HTTP 入口提供外部请求协议，补斜杠跳转保持 HTTPS。转发头不参与 namespace 授权或身份判断；认证仍由 publisher credential 决定。部署 smoke 同时检查 `/simple` 跳转到该 origin 的 HTTPS `/simple/`。

## 生产资源与 TLS

Registry 使用 Heroku app `inkcre-ext-reg-production`，其默认 origin 为 `https://inkcre-ext-reg-production-a6bbc8ada2d2.herokuapp.com`；web formation 为一个 Eco dyno。Neon 项目为 `wandering-base-13707928`，数据库 `registry` 位于根分支 `br-muddy-term-aw4iive7`。R2 使用原有私有桶 `inkcre-extension-registry-production-v2`。PR 分支从固定空 `preview-base` 创建，生产导入不改变这个基础分支。

Cloudflare zone `inkcre.dev` 中的 `registry.inkcre.dev` 使用代理 CNAME，目标为 Heroku 为该域名分配的 `classical-mapusaurus-sbqqxbde9bay1zrkw4vh1zhp.herokudns.com`。这个 hostname 的 Configuration Rule 设置 `ssl=strict`，Single Redirect Rule 将 HTTP 以 308 转向 HTTPS，并保留路径和查询参数；不修改其他 hostname 的 TLS 配置。

Registry 的 Cache Rule 对此 hostname 设置 `cache=true`、`edge_ttl.mode=bypass_by_default`、`browser_ttl.mode=respect_origin`、`origin_cache_control=true` 与 `respect_strong_etags=true`。页面和 API 的 `no-store` 禁止缓存；文件的 `public, no-cache` 要求边缘和浏览器每次回源重验证，不覆盖为固定 TTL。这样 release 的可读状态仍由应用在每次请求中检查，ETag 匹配时返回 304，边缘复用已经验证的字节。Cloudflare 默认 Browser Cache TTL 会把部分静态后缀改成四小时缓存，不能沿用这个默认值。切换后按 hostname 清除 Registry 缓存，不清除整个 zone。

Heroku SNI endpoint `gallimimus-68400` 绑定了仅覆盖 `registry.inkcre.dev` 的 Cloudflare Origin CA 证书，到期时间为 **2041-09-09 06:29 UTC**。公开客户端校验 Cloudflare 边缘证书，Cloudflare 校验 Heroku 的 Origin CA 证书；Heroku 默认域名仍使用平台的公开证书。此 app 不启用 ACM。Origin CA 不自动续期或发送到期通知，运维应在到期前签发新证书、用 `heroku certs:update` 替换并核验域名映射；私钥只保存在受限恢复目录与 Heroku 证书存储。保持 DNS 代理开启，关闭代理会将 Origin CA 证书直接暴露给不信任它的浏览器。参见 [Cloudflare Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/) 与 [Heroku SSL](https://devcenter.heroku.com/articles/ssl)。

## 首次切换

1. 明确来源 D1、目标 PostgreSQL、R2 桶、Heroku app、公开路由和获准变更窗口。先验证空库迁移、快照导入及整个发布流程；保存旧 Worker 版本与现有路由配置。
2. 暂停旧入口的发布写入并等待在途请求结束。本次使用 hostname 级临时 WAF 规则，拒绝 `registry.inkcre.dev` 的非 GET / HEAD / OPTIONS 请求，并实测规则生效；旧 Worker 的 workers.dev 和版本预览入口均关闭。停止 Web、Toolkit、CI publisher 等所有写入来源；只读分发可以继续。不要在旧入口仍接收写入时进行最终导入，也不要引入临时双写。
3. 使用 Wrangler 的 `d1 export <database> --remote --output <private-snapshot.sql>` 保存最终快照。来源 ID 显式传入，不从已删除的 Worker 配置猜测。限制快照文件权限；它包含凭据哈希和私有元数据。用 SQLite 将这份受信任导出转换成临时 SQLite 文件，执行完整性与外键检查。原始 token 从不进入快照。
4. 对空目标运行 `pnpm db:migrate`，然后运行 `pdm run python -m inkcre_extension_registry.import_d1 <snapshot.sqlite>`。导入器拒绝非空目标，在同一事务中转换内部 ID 并核验每张表全部逻辑字段的规范化内容摘要；任何失败回滚全部导入。旧时间戳、空值、JSON、凭据哈希、release 状态及 R2 key 都参与比较。
5. 再运行同一命令并加 `--verify-only`。保存仅含行数和摘要的报告；抽查既有 wheel、Core Metadata、MF manifest / assets 的实际 R2 内容与公开身份。导入不移动、重写或公开 R2 对象。旧 `migrations/` 是来源 schema 历史，包内 Tortoise 迁移是新库 schema 历史。
6. 启动已验证镜像，先通过 app origin 验证只读目录、详情、私有认证和原生协议。预先完成 Heroku 域名及回源证书配置并校验证书与主机名，再移除 Worker Custom Domain、创建上述代理 CNAME。按 hostname 清除旧缓存，等待路由收敛，并验证缓存、ETag、GET / HEAD、Simple 内容协商及下载。再次导出旧 D1，确认隔离后摘要仍与导入来源相等，随后移除临时 WAF 写入暂停规则，恢复新服务的发布能力。
7. 保存最终来源快照、导入摘要、镜像 revision、数据库迁移位置及路由验收。旧 D1 / Worker 的删除须在约定保留窗口后另行执行，不能以 PR 合并代替资源删除授权。

## 故障恢复

切流前任何失败都维持旧入口的写入暂停，调查目标库和对象状态后重试；如果取消切换，可恢复旧入口写入。导入器不会清空已有目标，失败后只有在确认它是本次专属迁移目标时才能重建。

新库尚未接受写入时，可以恢复旧路由与旧 Worker。新库已经接受写入后，旧 D1 不再完整；此时先停止新写入并保全两侧数据，通过修复新服务或经核验的数据合并恢复。直接回退旧 Worker 不能声称无损恢复。

PostgreSQL 事务不覆盖 R2。中断上传可能留下不可达 staging 对象；公开可见性仍由数据库关联和 release 状态决定。后续修复追加迁移，不回写已部署历史，也不使用 `--fake` 掩盖 schema 与迁移记录不一致。

## 本次迁移的恢复坐标

旧 Worker 为 `inkcre-extension-registry`，保留版本 `ef4f71a1-a596-4b91-a33c-e78835e5b015`；旧 D1 为 `af52114f-55b5-476f-b986-8ff8d8601d77`。它们不再承接公开流量，不作为新 PostgreSQL 写入后的实时副本。删除旧生产资源仍需单独约定保留窗口和授权。

最终 SQL / SQLite 快照、逐表逻辑摘要、R2 内容摘要、旧路由与 Worker 设置、回源证书私钥等恢复材料存放在执行机的 `~/.local/state/inkcre/ext-reg/production-cutover-2026-09-13/`。目录权限为 0700，文件为 0600；其中含凭据哈希和私钥，不得上传到 Git 或公开日志。生产运行凭据由 GitHub production environment 和 Heroku app 配置持有，owner 连接仅保留在交付权限边界内。
