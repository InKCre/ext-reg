# Registry Control Plane

## Authority Boundary

The Registry owns Extension Name and Nickname, strict-SemVer Release identity
and lifecycle, publisher scope, provenance, and typed associations to native
Python and Module Federation Distributions. Native package metadata remains
owned by its ecosystem. Deployment installation, Peer enablement, and runtime
activity are not Registry state.

There is deliberately no generic target manifest, cross-format artifact, or
Registry-owned compatibility predicate. One Release may independently append
one Python association and one Module Federation association; either is
optional. Association metadata, filenames, and bytes are immutable. Identical
retries are idempotent; conflicts require a new Release.

`preparing` is private and publication requires at least one admitted native
Distribution. `published` and `yanked` preserve descriptors and bytes;
`blocked` is a separate operator read-denial state.

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

## Persistence and Security

持久化由 PostgreSQL 与 Tortoise ORM / asyncpg 承担。`service/database.py` 定义模型、业务唯一约束、外键和状态约束；`service/repository.py` 拥有查询与事务。Release、Distribution 和 File 使用独立内部主键，公开身份仍是 Extension Name / Version 或 Python Project / Version / Filename。内部 ID 不进入公开 URL 或契约。

准备关联时，namespace 行锁串行化同一发布者的身份创建，release 行锁保护关联和状态。唯一约束保证 Python Project / Version 不被另一个 release 占用；失败会回滚同一事务中的 Extension、Release 和关联创建。上传、发布、撤回和恢复均重新检查锁定后的 release 状态。关联、文件名和内容身份不可变，相同提交可以重试。模型的联合约束明确使用数据库外键列名；不依赖迁移生成器猜测关系字段的物理列名。

R2 的网络访问不持有数据库事务锁。boto3 的同步调用在线程中执行；上传先写内容寻址的 staging 对象，再在 PostgreSQL 事务中增加可见关联。发布前检查关联对象存在，文件大小一致。失败可能留下不可达的 staging 对象，它们不是公开状态的来源。每次文件读取先检查 release 可读性，再通过 S3 流式返回；HEAD 只读取对象元数据。响应使用 `Cache-Control: public, no-cache` 和内容 SHA-256 ETag；条件 GET / HEAD 在 release 可读、对象存在之后才能返回 304。缓存必须逐次重验证，blocked 的 451 响应使用 `no-store`。已经被客户端下载的内容无法通过服务端状态变化收回。

应用启动只初始化连接池，不建表、不运行迁移、不创建凭据或示例数据。交付在启动新版本前运行包内 Tortoise 迁移，并仅允许向前执行。数据迁移工具只在旧 SQLite 快照读取边界使用 SQL，PostgreSQL 业务读写与发布凭据维护使用 ORM。角色与 GRANT 是 PostgreSQL 原生授权 DDL，由追加迁移维护；登录密码由可信交付端设置。运行角色 `registry_app` 仅获得七张业务表的 SELECT / INSERT / UPDATE / DELETE、对应序列的 USAGE 和 schema 的 USAGE，不能修改 schema、角色或迁移记录。后续新增表须在同一迁移显式授予所需权限，不自动授权全部未来表。旧 D1 历史保留用于导入验收，迁移工具不自动访问生产 D1。

Publisher 持有 namespace 范围内的发布能力；原始 token 只用于请求认证和运维命令的标准输入，数据库保存 SHA-256。匿名读取只能看到公开或撤回的 release，blocked 状态拒绝描述和原始文件访问。预览服务只获得所属数据库分支和 R2 桶的凭据；云平台控制凭据只属于可信交付控制器。

Registry 验证文件结构与完整性，不证明发布者可信。Python 扩展在受信任 Core 进程中运行，Module Federation Remote 获得宿主页面权限；Host 继续拥有兼容性判断和运行时协商。
