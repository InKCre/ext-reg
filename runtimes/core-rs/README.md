# InKCre Rust Extension SDK

`inkcre-extension-sdk` 提供独立 executable 扩展的协议类型与异步 runner。
它不依赖 Registry 或 Core。Registry 的 Rust 原生分发采用同一 executable 协议，
发布/下载约定见 [Rust 分发](../../docs/30-unit-tdd/rust-distribution.md)。
持久化和业务能力可由扩展自行采用 `inkcre-core` SDK 直连已准入 PostgreSQL。

```bash
cargo fmt --manifest-path runtimes/core-rs/Cargo.toml --check
cargo check --manifest-path runtimes/core-rs/Cargo.toml --all-targets --locked
cargo clippy --manifest-path runtimes/core-rs/Cargo.toml --all-targets --locked -- -D warnings
cargo build --manifest-path runtimes/core-rs/Cargo.toml --example echo --locked
```

这几条命令不编写或运行自动化测试。示例实现 initialize/start/invoke/stop 全程，
stdout 保留给协议，日志写 stderr。可从终端显式执行关键端到端验收：

```bash
python3 runtimes/core-rs/scripts/accept_echo.py
```

宿主安装示例需要与 executable 放在一起的 JSON manifest：

```json
{
  "schema_version": 1,
  "name": "example/echo",
  "version": "0.1.0",
  "distribution": "rust_stdio",
  "host_sdk": "core-rs",
  "host_sdk_version": "^0.1.0",
  "protocol_version": 1,
  "executable": "echo",
  "sha256": "替换为该可执行文件的64位小写SHA256"
}
```

相对路径必须位于 manifest 目录内；manifest 与 handshake 身份、SDK 条件和协议
必须匹配。宿主复制并验证可信产物后才保存精确选择，不会从 HTTP 请求任意路径执行文件。
业务调用只在 start 完成后进入 `Extension::invoke`。扩展有当前 Peer 传入的身份与
config/state 启动快照；需要读取最新业务 state 或原子写入时，使用已准入数据库协议，
不要把快照当作最新值整对象覆盖。

普通命令每帧包含换行最多 1 MiB；已声明 HTTP ingress 的已启动扩展，其
`http_request` 使用独立的 64 MiB 帧上限。宿主拥有超时、精确选择复核和进程回收；扩展作者负责
业务副作用与幂等性。原生 executable 是可信代码，进程边界不是安全沙箱。

完整运行边界见 [Rust SDK 设计](../../docs/30-unit-tdd/rust-extension-sdk.md)。

## 业务能力

`Descriptor.capabilities` 显式声明 Resolver、Storage、Source 和 Job 能力。空声明表示
只有通用调用；`methods` 中出现一个名字不会自动成为业务 handler。能力的数据结构
位于 `src/capabilities.rs`，对应的 Core trait 与本机 registry 由 impl-rs 拥有。

扩展按声明实现 `Extension::resolver_read/resolver_draft`、
`storage_read/storage_create/storage_update/storage_delete`、
`source_collect/source_backfill` 或 `job_can_handle/job_execute`。runner 只向已声明的
类型分派相应固定命令，未声明或不支持的能力明确返回 `unsupported_capability`。
通用 `invoke` 与这些入口分别管理。Resolver 自定义读方法具有 `get_` 或 `read_`
前缀和参数 schema；Source 不支持历史采集时将 backfill schema 保持为 null。

SourceRequest 包含 source/type/job ID 和本次命令 config；插件通过自己的 Core 连接
读取最新 Source 配置、state 与 cursor。SourceOutcome/JobOutcome 的 `state` 是 Job
状态对象 patch，不是整份 Source.state 或部署 Extension.state 的替换。Job eligibility
发生在领取前，`job_can_handle` 应只判断可执行性，不提前执行工作。

Source/Job 执行由 Job timeout 和取消控制，不受通用 invoke 的 20 秒上限约束。
短 RPC 的期限包含协议锁排队；仅排队超时不会终止另一个正在执行的工作。
Storage bytes 使用 JSON 字节数组，仍须遵守每帧 1 MiB 限制。取消、进程恢复和外部
Storage 的事务边界见[能力注册与撤销](../../docs/30-unit-tdd/rust-extension-sdk.md#typed-业务能力与撤销)。

## HTTP ingress

`Capabilities.http_ingress` 声明扩展自己的 HTTP route 与 Peer inbound。每条 route
明确 method、path、path_match（exact/prefix）和 auth（peer/protocol/public）。默认
peer 表示 Host 先验证 Peer JWT；protocol 表示插件拥有并实际执行外部协议认证。
公开观察必须显式写 public。前缀按路径段匹配，精确路由优先，再选择最长前缀。

`HttpIngress::validate_mount(name)` 把路径限定在 `/{extension name}` 根及其子路径；
Host 还必须拒绝不同 namespace 的同名 mount 冲突。`admit(method,path)` 是 Host 与
runner 共享的精确 admission。路径为一次解码后的值，不含百分号、dot 段或 query；
Host 不得让 HTTP framework 在 admission 后再次规范化或解码。

`Extension::http_request(HttpRequest)` 返回 `HttpResponse`，body 在 Rust 中是
`HttpBody(Vec<u8>)`，wire 为标准 padded Base64 string，decoded HTTP body 最多
45 MiB，足以容纳产品 JSON 内已编码的 32 MiB Memos attachment。具体产品继续
自行执行更小的语义限额。headers 保留同名重复与非 UTF-8 bytes；Host 负责剔除
hop-by-hop/framing headers，并从真实请求建立 authority，不能相信转发者提供的
内部 mount 或认证标记。SDK 的 typed 数据和固定分派不授予认证。

显式运行真实 executable 的关键协议验收：

```bash
cargo build --manifest-path runtimes/core-rs/Cargo.toml --example http_echo --locked
python3 runtimes/core-rs/scripts/accept_http.py
```

该脚本覆盖协议认证、路径/方法拒绝、45 MiB bytes 完整往返、普通命令保留 1 MiB
限制及正常停止，不接入自动化测试套件。Host 的实际 HTTP/JWT 与挂载生命周期仍由
各 Host 自身验收。详细字段、准入和兼容策略见 [SDK 设计](../../docs/30-unit-tdd/rust-extension-sdk.md#http-ingress)。
### 仅加载持久资料读取能力

提供 exact Resolver 或 Storage 读取能力的扩展可声明 `capabilities.passive_knowledge = true`。宿主在保留已安装 Decoder、且当前 Peer 停用扩展时，为该精确产物选择 `start_knowledge`。该启动只携带 `peer_id`，作者在 `Extension::start_knowledge` 中打开读取或 drafting 所需的资源，并由 `stop_knowledge` 对称关闭。

此进程只处理声明的 `resolver_read`、`resolver_draft` 与 `storage_read`。Source、Job、HTTP 路由、通用 invoke 和 Storage 写操作由普通启动模式处理。一次进程生命周期只选一种模式，切换由宿主通过新进程完成。未声明此能力的 executable 维持原有启动行为和 wire 形状。
