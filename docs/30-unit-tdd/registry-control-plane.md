# Registry Control Plane

## Authority Boundary

Registry 以 `(Extension Name, distribution, version)` 标识独立不可变发行。`distribution` 为 `python` 或 `module_federation`，各生产者独立决定版本、准备、上传与发布；同一 Extension 的两种分发无需共用版本。Registry 保留名称、昵称、发布者权限、来源与生命周期，不拥有部署安装、Peer 启用或运行事实，也不解析插件业务数据兼容性。

v2 prepare 只接受路径指定的一个原生元数据对象。关联元数据、文件名与字节不可变；相同提交幂等，冲突需要新版本。`preparing` 私有，自己的全部对象完整才能发布。`published` 和 `yanked` 保留描述与字节；`blocked` 拒绝读取。不存在跨分发 solver、中央业务协议或全格式一次发布要求。

v1 仅保留历史统一发行读取；所有旧控制写入返回 410。新独立发行不进入 v1 目录。历史 DTO 不增加 distribution 字段，迁移时冻结当时已具有文件的可见关联，不能用后来完成的空关联改变历史 DTO。历史描述与全局文档采用保守状态投影：旧发行状态及关联原生状态共同约束，任一关联 blocked 不能经旧入口绕过。类型明确的 wheel/MF URL 检查自己的原生状态。

## Native Admission and Reads

The Python surface admits bounded wheel uploads through `/legacy/`, validates
the declared digest, filename, normalized project, version congruence, Core
Metadata, entry point, and archive safety, then exposes PEP 503/691 and PEP 658
projections through `/simple/` and `/packages/`. The request is declared-length
and capped at 20 MiB. CPython uses Starlette's standard spooled multipart files.

The Module Federation surface admits a bounded ZIP rooted at
`mf-manifest.json`, validates its relative Remote entry and referenced assets,
and materializes only the manifest's public path from canonical
`PUBLIC_ORIGIN`. It does not mint a second public manifest schema.

The generated [OpenAPI contract](../../contracts/openapi.json), JSON Schemas,
models, routes, generated contracts, and build checks are the exact executable interface authorities.

## Extension Documentation

Documentation is a separate projection of one exact Release, not another Distribution and not an
optional field added to `ReleaseRecord`. 新文档按精确 native 坐标与 `global` 或本分发 scope 寻址；其他分发 scope 被拒绝。历史 global 快照保留旧发行 owner，不能猜测归属并迁成某个 native 发行。 Each publication submits a complete ZIP through POST, with a required
`expected_etag` business field: null creates an absent set, while the observed strong ETag permits
a correction. Every new publication uses a fresh opaque snapshot identity and origin.

Registry validates normalized paths, admitted static media types, expansion limits, the HTML entry,
and the declared content digest. It stages every object before a short transaction locks the Release,
rechecks the precondition, records the immutable snapshot, and moves the current-set pointer. Failed
staging and stale editors cannot replace the previous pointer. The Toolkit saves the archive,
metadata, snapshot identity, and precondition as one candidate. The snapshot ETag fingerprints the
canonical target, metadata, and original precondition; the atomically committed snapshot is also
the publication receipt. An exact replay returns that historical receipt before checking current,
without staging again, changing the pointer, or changing its timestamp. Reusing an ID with a different
fingerprint conflicts. The receipt exposes `committed_at` and `snapshot_etag`, not a current-set HTTP
ETag. Authentication and blocked checks apply before acknowledging a replay.

Toolkit makes at most two foreground attempts for transport failures, selected temporary 5xx, or an
invalid receipt. Exhaustion reports an unknown outcome and retains the saved candidate. Definitive
client errors are not retried. There is no background recovery, eventual-delivery guarantee, or
automatic adoption of a newer ETag. Staging failure can leave unreachable objects; commit receipts
confirm a past database transaction, not the continuing availability of every stored byte.

作者的构建、上传限制、MIME 映射及恢复方式以[静态文档发布协议](documentation-admission.md)为准。JSON Schema 包含 upload、publication、receipt、release 和 hosting 契约；OpenAPI 的 multipart `metadata` 是 JSON 编码的 publication 文本字段，其 `contentSchema` 给出内部结构，HTTP 错误与写入前提也在 OpenAPI 中声明。

Management and content use separate origins. The stable management entry redirects to the selected
snapshot; files, root-relative assets, browser storage, and Service Workers remain confined to that
snapshot's origin. The content-origin middleware serves only GET and HEAD, never management routes,
credentials, author headers, redirects, or server execution. Exact and directory-index routes are
supported, with `.html` clean URLs; there is no SPA fallback. Published and yanked Release snapshots
remain readable, with a withdrawal warning on stable yanked entries. `preparing` is publisher-only,
and `blocked` denies discovery, stable entries, and every historical snapshot before revalidation.

## Persistence and Security

持久化由 PostgreSQL 与 Tortoise ORM / asyncpg 承担。`service/database.py` 定义模型、业务唯一约束、外键和状态约束；`service/repository.py` 拥有 Release、Distribution 与发布身份的查询和事务，`service/documentation.py` 的 `DocumentationRepository` 拥有文档查询、对象 staging 和 current-set 替换事务。两者由 lifespan 创建，共享同一个 `ArtifactStore`；文档仓储不依赖另一个仓储的实例或内部状态。不可变对象的暂存、批量存在性检查、并发额度与失败取消统一由 `service/storage.py` 管理，业务仓储只决定对象身份及事务提交。批处理退出并完成兄弟任务清理后，存储层重新抛出原始异常，使冲突保留其领域类型。Release、Distribution 和 File 使用独立内部主键，新公开发行身份是 Extension Name / Distribution / Version，原生文件仍是 Python Project / Version / Filename。内部 ID 不进入公开 URL 或契约。

文档指针由 PostgreSQL 的 `(snapshot_id, release_id, scope)` 复合外键保证归属一致。Tortoise 保留单列关系用于查询，复合外键由 `0004_documentation_ownership` 原生 DDL 补充；已有指针不能关联其他 Release/scope，所指快照也不能在保留该指针时改变归属。`0006` 对新 native owner 增加同等复合外键，并以 XOR 约束保证每个快照与指针恰有一个历史或原生 owner。

准备关联时，namespace 行锁串行化同一发布者的身份创建，release 行锁保护关联和状态。唯一约束保证 Python Project / Version 不被另一个 release 占用；失败会回滚同一事务中的 Extension、Release 和关联创建。上传、发布、撤回和恢复均重新检查锁定后的 release 状态。关联、文件名和内容身份不可变，相同提交可以重试。模型的联合约束明确使用数据库外键列名；不依赖迁移生成器猜测关系字段的物理列名。

`ArtifactStore` 的同一进程内额度为 4，由文档、MF 暂存及发布检查、Python 文件暂存共同使用；不同类型上传之间不再拥有独立额度。直接下载不经过该额度。对象存储策略的变更集中在此处，但需要一起考虑这些调用方的等待时间；它不是部署范围的限流或公平调度承诺。

已知的冲突、状态与查找异常定义在 `service/errors.py`，由 FastAPI exception handler 统一转换为既有 HTTP 状态和 `detail` 响应结构；对象大小冲突的消息统一为 `staging object size conflict`，未知异常继续传播。内容域 middleware 不经过管理路由，仍在自己的边界转换读取错误。

S3 的网络访问不持有数据库事务锁。boto3 的同步调用在线程中执行；上传先写内容寻址的 staging 对象，再在 PostgreSQL 事务中增加可见关联。发布前检查关联对象存在，文件大小一致。失败可能留下不可达的 staging 对象，它们不是公开状态的来源。每次文件读取先检查 release 可读性，再通过 S3 流式返回；HEAD 只读取对象元数据。响应使用 `Cache-Control: public, no-cache` 和内容 SHA-256 ETag；条件 GET / HEAD 在 release 可读、对象存在之后才能返回 304。缓存必须逐次重验证，blocked 的 451 响应使用 `no-store`。已经被客户端下载的内容无法通过服务端状态变化收回。

应用启动只初始化连接池，不建表、不运行迁移、不创建凭据或示例数据。交付在启动新版本前运行包内 Tortoise 迁移，并仅允许向前执行。数据迁移工具只在旧 SQLite 快照读取边界使用 SQL，PostgreSQL 业务读写与发布凭据维护使用 ORM。角色与 GRANT 是 PostgreSQL 原生授权 DDL，由追加迁移维护；登录密码由可信交付端设置。运行角色 `registry_app` 仅获得明确列出的业务表的 SELECT / INSERT / UPDATE / DELETE、对应序列的 USAGE 和 schema 的 USAGE，不能修改 schema、角色或迁移记录。后续新增表须在同一迁移显式授予所需权限，不自动授权全部未来表。旧 D1 历史保留用于导入验收，迁移工具不自动访问生产 D1。

Publisher 持有 namespace 范围内的发布能力；原始 token 只用于请求认证和运维命令的标准输入，数据库保存 SHA-256。匿名读取只能看到公开或撤回的 release，blocked 状态拒绝描述和原始文件访问。预览服务只获得所属数据库分支和 R2 桶的凭据；云平台控制凭据只属于可信交付控制器。

Registry 验证文件结构与完整性，不证明发布者可信。Python 扩展在受信任 Core 进程中运行，Module Federation Remote 获得宿主页面权限；Host 继续拥有兼容性判断和运行时协商。

## 原生发行完整性与迁移

发布检查只覆盖当前原生发行自己的全部字节：Python 至少一个 wheel 及其 metadata，MF 为 manifest 与全部资产。对象检查不持有数据库锁；提交前锁定原生发行并重新读取文件与 snapshot 身份，检查期间新增文件会导致 409，发布者可重试当前集合。

`0005` 为历史每个关联生成独立原生坐标并重挂原有关联；保留文件主键、R2 key、时间、来源及原生元数据。历史 published/yanked 关联若没有 wheel 或 MF manifest，原生状态降为 preparing；blocked 保留。`0006` 为新文档增加 native owner，不修改已有快照、receipt、稳定 URL 或历史 owner。非空旧 schema 回放、D1 导入对照及真实 HTTP 检查共同验证此边界。部署只前进迁移，不把新的应用回退到只能解释统一发行的版本。
