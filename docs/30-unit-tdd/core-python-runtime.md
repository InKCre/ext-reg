# Core Python Extension Host Runtime

This document owns the expensive lifecycle contract of the independently released
`inkcre-extension-runtime-core-py` package. Core business capability semantics remain owned by the Core repository and the
shared Hub.

## Registration And Active Effects

```text
entry-point import -> process-monotonic capability type registration
Extension start    -> exact active routes + Peer inbounds + public claims
Extension stop     -> withdraw those exact active effects
package replacement -> process restart
```

Imported Source、Resolver and Sink classes remain registered for the lifetime of the interpreter. Disable does not restore
an earlier registry map or simulate Python module unload. This preserves decoder availability for persisted Blocks and avoids
pretending that `sys.modules` plus transitive imports can be rolled back safely.

One startup retains only the route objects and Peer inbound capability IDs it actually published, plus its exact public-route
claim. Stop and failed-start cleanup remove those identities without reconstructing a global before-state, so unrelated later
registrations are not overwritten. Source catalog persistence synchronizes the current monotonic registry explicitly after a
successful startup.

An imported exact Project version remains the process boundary. Install/upgrade may replace a Distribution only when no Peer
is enabled, but a process that imported the previous Project must restart before executing the replacement. Re-enable of the
same loaded version uses ordinary entry-point loading and the retained Python modules; active routes and Peer inbounds are
published fresh.

## Module Ownership

`DistributionModules` uses standard entry-point loading and verifies that every loaded module in the canonical
`extensions.<name>` package resolves to a file owned by the acquired Distribution. It does not delete, restore or shadow
`sys.modules`, and it does not create a second import cache.

## 异步 Host 持久化能力

Runtime 0.1.4 增加 `update_config_async`、`get_state_async`、`mutate_state_async`、
`mutate_config_and_state_async` 和 `on_start_async`。它们只调用 Host model 对应的 async capability；
不会调用旧同步方法、在线程中运行数据库代码，或创建数据库 session。旧同步入口继续供旧 Host 使用，
Host 必须明确选择与其持久化模型一致的入口。现有 `ExtensionManager` 仍使用旧同步 Host 合同；
这些新增入口供 Core 自己的 async Host adapter 采用，不代表旧 Manager 已整体异步化。

Host model 需要提供 `update_config_async`、`read_state_async`、`mutate_state_async`、
`mutate_config_and_state_async` 与 `update_config_schema_async`。配置和 schema 更新返回刷新后的
Host model，状态读取返回 persisted JSON。变更方法必须在 Host 的事务内调用同步 transform，
提交成功后才能返回；事务、行锁及并发控制仍由 Host 拥有。Runtime 恢复 typed 输入后保留 transform
产出的 typed 结果，避免内部传递时再次恢复。`get_config()` 仍只恢复已绑定 model 的 config 投影。

`on_start_async` 复用同步启动的 publication scope，先发布资源，再 await
`SourceManager.sync_source_types_async()` 和 Host schema 持久化。普通 Source/Resolver class 注册
仍是同步的进程内操作；Source catalog 写入必须 await。启动完成后才报告 `runtime_active()`；同一个
Extension 启动期间再次启动会失败。任何失败或取消都会撤销本次 routes、Peer inbounds 和 public claims，
随后允许重新启动。进程内已 import 的 decoder/type 注册继续保留，不模拟 module unload。

这一变化不改变 Registry、installed、enabled 或 public-route 合同，也不让旧 wheel 自动兼容新的
Core async-only API。采用方必须分别声明 Runtime 包版本与 Core Host SDK 版本窗口，并验证真实
Host 的事务实现。Runtime 层的 scripted 验证可证明 await、typed round trip 和 publication 清理，
不能替代 Core 对 PostgreSQL 提交、回滚及行锁的验证。
