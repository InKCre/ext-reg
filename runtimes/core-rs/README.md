# InKCre Rust Extension SDK

`inkcre-extension-sdk` 提供独立 executable 扩展的协议类型与异步 runner。
它不依赖 Registry 或 Core；本阶段没有 Rust Registry 发布/下载接口。
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

每帧包含换行最多 1 MiB。宿主拥有超时、精确选择复核和进程回收；扩展作者负责
业务副作用与幂等性。原生 executable 是可信代码，进程边界不是安全沙箱。

完整运行边界见 [Rust SDK 设计](../../docs/30-unit-tdd/rust-extension-sdk.md)。
