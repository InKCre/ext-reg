# 生产 Registry 与 PostgreSQL 切换

公开 origin 保持 `https://registry.inkcre.dev`。2026-09-13 起，由一个运行于 Heroku Eco dyno 的 CPython / FastAPI 服务容器、Registry 专属 Neon PostgreSQL 项目和既有私有 R2 桶提供服务。Web、API、静态资源和原生分发由同一镜像交付。旧 Worker / D1 已退出公开路由，保留为本次迁移的恢复依据。

`production.yml` 只接受精确 current-main SHA。`verify` 执行仓库检查、使用该 production 环境的既有 Heroku 凭据只读查询指定 app 并确认 container stack，然后构建镜像。401、app 不可访问或非 container stack 均在维护前暴露；不要求 web=0，不访问数据库或修改配置、release、formation。这个预检证明当前 app 读取可用，不模拟发布写入，也不保证凭据在以后仍有效。`deploy` 同样执行只读预检，在受保护 production 环境中重新核验 main 后，对已配置 app 向前迁移、配置数据库和单桶 S3 凭据、发布同一镜像，并验证 Heroku app origin。它不自动导入 D1、不改变域名、不创建示例数据，也不删除旧资源。

production 环境需要 `HEROKU_APP_NAME`、`S3_ENDPOINT_URL`、`S3_BUCKET`、`DOCUMENTATION_ORIGIN_TEMPLATE` variables，以及 `HEROKU_API_KEY`、`MIGRATION_DATABASE_URL`、`DATABASE_URL`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY` secrets。文档模板必须指向已经配置 wildcard DNS/TLS 的专用内容 origin。生产当前使用 `https://registry-docs-{snapshot}.inkcre.dev`；每个不可变快照拥有独立 origin。为复用免费 TLS，DNS 与证书使用范围更宽的 `*.inkcre.dev`，而不是只能匹配这类文档 hostname 的多层 wildcard。这个 catch-all 只负责把请求送达 Registry；应用仍按 `DOCUMENTATION_ORIGIN_TEMPLATE` 精确解析 Host，其他落入 wildcard 的 hostname 返回 421。DNS 解析成功或 TLS 握手成功都不代表该 Host 是文档 origin。内容域与管理站同属 `inkcre.dev`，因此部署接受作者 HTML/JS 可能接收或干扰父域 Cookie 的风险；`inkcre.dev` 下的服务不得设置可发送到内容域的敏感父域 Cookie。首次配置保持既有 R2 桶，S3 token 仅授予该桶的对象读写。`MIGRATION_DATABASE_URL` 使用 `registry_owner`，仅交给迁移容器与可信角色配置命令；`DATABASE_URL` 使用同一数据库的普通 `registry_app` 角色和独立密码。迁移创建该角色及业务表授权，控制器设置密码后以 `web=1:eco` 启动应用。owner 连接与平台控制 token 不进入运行服务配置。数据库连接属于独立 Registry 项目，不复用 core-py 的数据库或发布生命周期。

Heroku 交付为 Uvicorn 设置 `FORWARDED_ALLOW_IPS=*`，由平台 HTTP 入口提供外部请求协议，补斜杠跳转保持 HTTPS。转发头不参与 namespace 授权或身份判断；认证仍由 publisher credential 决定。部署 smoke 同时检查 `/simple` 跳转到该 origin 的 HTTPS `/simple/`。

## 当前 PostgreSQL 原生发行切换

生产 Registry 已于 2026-10-13 完成原生发行 v2 切换，服务来源为 `ab5a225f632a83c067269f92967b2307ba79c1b1`，数据库迁移位置为 `0006_auto_20261013_1914`。正式发布资产为 Toolkit 0.5.0、Python Runtime 0.2.0 和 Web Runtime 0.4.0；合并后的 controller 修复不意味着生产服务已部署到新的 main。

0005/0006 将分发关联改为原生发行坐标，保留历史文件、R2 key、URL 和文档 receipt。迁移后的关联不能由旧镜像解释，因此这种切换必须有维护窗口，不能只暂停发布写入而保持旧服务读取。合并 main 会触发独立 SDK 包资产发布；Registry 服务迁移与镜像发布仍由 `production.yml` 手动执行。

1. 固定已验证的 current-main SHA，先运行 `operation=verify`。保存当前镜像 revision、数据库迁移位置、数据库可恢复快照及历史下载和文档身份摘要。
2. 暂停所有 publisher 并等待在途请求结束。由获准的操作员将既有 app 的 web formation 缩至 0，等待旧 web dyno 停止；维护窗口内不允许其他操作员或自动化重新扩容。Heroku maintenance 页面或 Eco 休眠不能替代停止进程。
3. 对同一 SHA 运行 `operation=deploy`。控制器在任何数据库、配置和发布变更之前读取 [Heroku Formation Info 和 Dyno List](https://devcenter.heroku.com/articles/platform-api-reference)。它要求 web quantity 为 0，且完整 dyno 列表中的 web 状态仅为 down/crashed；idle、starting、up、未知状态及不完整列表均拒绝。不自动停机，也不自动回滚。
4. 控制器依次迁移、配置 runtime 登录和 app、推送目标镜像、发布镜像、恢复 `web=1:eco`，最后验证 exact `/livez`。再检查 v1 历史只读、旧写 410、v2 坐标、原 wheel/MF 字节与文档 receipt，确认后恢复已采用 v2 的 publisher。恢复 publisher 不包含新 Extension 正式发行授权。

日志以 app、目标 revision 和 phase 标识失败位置，并立即 flush，使非交互 runner 在 provider 操作完成前也能看到当前阶段。migration 或 release 失败时控制器不执行 scale-up，保持旧进程停止；调查迁移记录及实际 release 后，以兼容当前 schema 的镜像向前恢复。smoke 失败发生在新镜像已启动之后，不能当作部署未发生；保持 publisher 暂停，核验实际 revision 和服务状态后修复。迁移后直接启动旧镜像不是安全回滚。恢复旧数据库快照需要单独确认维护期间的写入及恢复范围，不能把 schema 不兼容视为自动回滚依据。

本次 PostgreSQL 恢复材料位于执行机的 `~/.local/state/inkcre/ext-reg/native-v2-cutover-2026-10-13/`，目录为 0700，dump、逻辑数据、原凭据状态和 receipts 为 0600。维护前和停止旧 web 后分别保存一致快照；最终 `final.dump` 的 SHA256 为 `d7f682c89a1464d23d68809a2479c5860711cc03b80a2ebfed15cf39ebfbe574`。两份快照均在隔离 PostgreSQL 17 实际恢复并逐字节核对规范逻辑数据；生产快照的 0005/0006 重放也通过。备份包含凭据哈希和私有元数据，不得上传到 Git 或公开日志。

上海时间 2026-10-13 23:41:10 停止旧 web，23:55:30 确认新服务 smoke 成功，次日 00:03:08 恢复原先活跃的 1 行 publisher，00:06:10 完成 ready 确认。旧 controller 的 stdout 缓冲使 phase 日志时间集中，因此 23:55:30 是 smoke 成功日志的确认点，不是精确进程启动时间。验收核对了 42 个原生发行读取、149 个历史公开对象哈希、文档 snapshot/ETag/旧入口身份、旧写 410，以及全部凭据哈希和原停用状态保持；没有为身份测试创建发行或新 token。生产 raw publisher token 不在执行机，独立的 HTTP 认证只读探测未做，后续既有 producer 使用其现有 production secret 完成真实发布认证。

首次部署因 GitHub production 环境的旧 `HEROKU_API_KEY` 失效，在读取 app 的 `stopped_web_check` 阶段返回 401，未进入数据库迁移。操作员确认 schema、旧 release、formation 和恢复材料未变后，将同名 secret 更新为同一现有 Heroku 主体的有效授权，再对同一精确来源重试成功；没有新建 token、增加权限或修改数据库/R2 凭据。这也是维护前只读凭据预检与即时阶段日志的必要性。

以下 D1 导入、路由切换和恢复坐标记载的是 2026-09-13 的历史迁移。其旧入口只读可继续的做法，不适用于上述同库不兼容迁移。

## 生产资源与 TLS

Registry 使用 Heroku app `inkcre-ext-reg-production`，其默认 origin 为 `https://inkcre-ext-reg-production-a6bbc8ada2d2.herokuapp.com`；web formation 为一个 Eco dyno。Neon 项目为 `wandering-base-13707928`，数据库 `registry` 位于根分支 `br-muddy-term-aw4iive7`。R2 使用原有私有桶 `inkcre-extension-registry-production-v2`。PR 分支从固定空 `preview-base` 创建，生产导入不改变这个基础分支。

Cloudflare zone `inkcre.dev` 中的 `registry.inkcre.dev` 使用代理 CNAME，目标为 Heroku 为该域名分配的 `classical-mapusaurus-sbqqxbde9bay1zrkw4vh1zhp.herokudns.com`。这个 hostname 的 Configuration Rule 设置 `ssl=strict`，Single Redirect Rule 将 HTTP 以 308 转向 HTTPS，并保留路径和查询参数；不修改其他 hostname 的 TLS 配置。文档内容使用 DNS-only CNAME `*.inkcre.dev`，指向 Heroku 分配的 `thawing-opossum-dgyx69y8psreeea1hcg8r0k0.herokudns.com`。精确的 `app`、`design`、`registry` 等记录优先于 wildcard；新增子域不得依赖 wildcard 的 Registry 421 响应作为正式路由。

Registry 的 Cache Rule 对此 hostname 设置 `cache=true`、`edge_ttl.mode=bypass_by_default`、`browser_ttl.mode=respect_origin`、`origin_cache_control=true` 与 `respect_strong_etags=true`。页面和 API 的 `no-store` 禁止缓存；文件的 `public, no-cache` 要求边缘和浏览器每次回源重验证，不覆盖为固定 TTL。这样 release 的可读状态仍由应用在每次请求中检查，ETag 匹配时返回 304，边缘复用已经验证的字节。Cloudflare 默认 Browser Cache TTL 会把部分静态后缀改成四小时缓存，不能沿用这个默认值。切换后按 hostname 清除 Registry 缓存，不清除整个 zone。

Heroku ACM 已为 `registry.inkcre.dev` 与 `*.inkcre.dev` 分别签发公开受信任证书。内容 wildcard 必须保持 DNS only，才能让 Heroku 验证并续期；若改为 Cloudflare proxy，必须先提供另一条可验证且由浏览器信任的完整 TLS 路径，不能让旧的 Cloudflare Origin CA 证书直接面向客户端。`registry.inkcre.dev` 仍可保持代理，因为其 Heroku origin 也有 ACM 证书。域名增删后运行 `heroku certs:auto --wait`，并分别验证合法但不存在的 snapshot Host 返回 404、非模板 Host 返回 421。参见 [Heroku ACM](https://devcenter.heroku.com/articles/automated-certificate-management) 与 [Heroku SSL](https://devcenter.heroku.com/articles/ssl)。

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

MF snapshot 上传和发布前的对象检查在进程内共享四个并发额度，每个请求最多运行四个对象 worker。它们复用现有 boto3 客户端；十条连接的保留池容量本身不限制并发。上传仍逐对象先 HEAD、缺失时 PUT，全部完成后才在 release 行锁事务内提交 association；发布仍等待全部关联对象可用。失败或取消会等待已启动的对象调用结束，部分 staging 对象可以由相同 snapshot 重试复用，不会提前成为公开关联。

服务输出 `mf_upload` 的 `receive`、`validation`、`lookup`、`staging` 和 `commit` 阶段完成日志，以及 `mf_publish phase=objects` 的检查日志。`duration_ms` 是该阶段墙钟耗时，`commit` 包含事务后的 descriptor 查询；日志以 extension/version 关联请求，不记录凭据或文件内容。排查 H12 时将这些日志与 Heroku request 日志对应，区分接收和 ZIP 校验、R2 往返、数据库提交；未完成阶段不会输出完成耗时。相同 release 的并行重试应结合请求时间判断，不能把相同身份的相邻日志当作同一个请求。

[Heroku H12](https://devcenter.heroku.com/articles/request-timeout) 表示路由器在 30 秒内没有收到响应，应用仍可能完成当前请求。上传得到 503 或连接超时不能证明提交失败。恢复时保留原 ZIP、prepare descriptor、source revision 和 build identity；重新查询发行状态，对相同候选幂等重试并在公开后核验全部字节。MF-only Release 在 `preparing` 时公共读取仍是 404，须通过已认证的 Publisher 状态检查或继续同一发行的 publish；对象尚未就绪的 409 可以有限等待，鉴权、内容冲突、yanked 或 blocked 不应作为临时错误重试。有限并发减少逐文件往返累积，不保证上游故障或大 snapshot 一定在路由超时内完成。

## 本次迁移的恢复坐标

旧 Worker 为 `inkcre-extension-registry`，保留版本 `ef4f71a1-a596-4b91-a33c-e78835e5b015`；旧 D1 为 `af52114f-55b5-476f-b986-8ff8d8601d77`。它们不再承接公开流量，不作为新 PostgreSQL 写入后的实时副本。删除旧生产资源仍需单独约定保留窗口和授权。

最终 SQL / SQLite 快照、逐表逻辑摘要、R2 内容摘要、旧路由与 Worker 设置、回源证书私钥等恢复材料存放在执行机的 `~/.local/state/inkcre/ext-reg/production-cutover-2026-09-13/`。目录权限为 0700，文件为 0600；其中含凭据哈希和私钥，不得上传到 Git 或公开日志。生产运行凭据由 GitHub production environment 和 Heroku app 配置持有，owner 连接仅保留在交付权限边界内。
