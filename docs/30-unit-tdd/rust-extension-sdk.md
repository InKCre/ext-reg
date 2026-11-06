# Rust executable Extension SDK

编写 Rust 扩展或为原生 Peer 实现宿主时阅读本文。`runtimes/core-rs` 的
`inkcre-extension-sdk` 是独立 Cargo crate，拥有 `rust_stdio` 本地分发格式、
版本化消息、扩展 trait 和 stdio runner，不依赖 Registry 服务或任一 Core 实现。
业务、共享信息和 Peer 参与语义继续由 Hub 契约拥有。

扩展是可信本地 executable，以独立子进程加载；宿主 HTTP app 自身仍可作为单个二进制分发。
进程隔离用于明确加载、更新与回收边界，不构成恶意代码 sandbox。SDK 不使用 Rust 动态库 ABI。

## 分发边界

当前只支持操作者显式提供的本地 manifest 和 executable。Registry 服务现有
Python/Module Federation 发布接口未扩充，不应把 Rust 本地安装描述为 Registry
发布、下载或完整性背书。Rust SDK 采用自身 Cargo 版本，原生安装 manifest 标识
精确 Extension name/version、宿主 SDK 条件、协议版本和 executable SHA-256。

manifest 数据结构和严格输入规则由 SDK `Manifest` 及 `validate` 拥有。
executable 是 manifest 目录内相对路径；宿主复制产物到自己的不可覆盖精确坐标目录，
校验复制后的摘要，再保存当前 Peer 的 selection。后续启动重新验证摘要与坐标。
更新需要新版本；保持旧进程运行时不能更换其精确 selection。

## 运行协议

stdin/stdout 使用 UTF-8 JSON-line，每帧（包含换行）最多 1 MiB。SDK 读取时逐块
检查边界，不先无界读入；stdout 只输出协议，日志写 stderr。请求包含
`protocol_version`、`id`、`method`、`params`。响应返回相同版本与 ID，并恰有
`result` 或 `error`；成功结果可为 JSON null。协议 v1 按顺序请求/响应，不提供并发
多路复用、宿主回调或任意 SQL RPC。

生命周期顺序为 `initialize`、`start`、零到多次 `invoke`、`stop`。initialize
返回插件精确身份、实际 SDK 版本、协议版本、config schema 和可调用方法。
宿主核对 manifest，校验当前共享 config 后发送 start；start 参数包含 Peer ID 和
当时共享 config/state 快照。快照不能被当作可盲目覆盖的最新 state。

数据库操作可由扩展显式采用 impl-rs core SDK 完成。宿主可通过 builder 显式授权
把执行端连接能力传给可信插件，使用 `INKCRE_DATABASE_URL` 子进程环境变量，
不会把连接串存入 manifest、参与记录或管理响应。SDK 本身不读取环境或建立数据库连接。
连接串、config/state 和业务请求可能含凭据，扩展作者不得把它们打印到日志或错误消息。

宿主为请求设超时，并在失败、停用、退出时关闭和回收子进程。SDK runner 维护
initialize/start/invoke/stop 状态机，收到 stop 后响应并退出；stdin 正常关闭时调用
活动扩展的 stop。强制结束不能保证插件自己的外部业务副作用已回滚。

## 持久参与与恢复

本地分发只提供已安装产物；`Peer × Extension` selection、enabled intent
和精确 config schema 仍保存在共享数据库。共享参与管理先提交意图再应用运行变化。
原生宿主的本机 disable 是明确例外：先按 Peer/Extension 保存本机停用标记并停止
进程，再尝试提交共享停用意图；数据库、凭据或授权失败不阻止本机停止，也不能被
报告为共享更新成功。本机标记只覆盖尚未同步的停用请求：共享停用提交成功后立即
清除；冷启动和周期收敛尊重未同步标记，重新连通后补提交共享停用并清除标记。
成功同步后继续消费之后新的共享 enabled，不用本机旧标记覆盖远端新意图。
显式 enable 也在成功提交启用意图后清除旧标记。移除参与先停止本机进程、提交停用，
再删除该 Peer 的参与记录，完成后清除标记。标记不复制业务数据或安装坐标权威，
管理状态同时展示表示未同步本机停用的 `locally_disabled` 与共享 `enabled`。
initialize 验证后条件提交该选择的 schema，再校验配置并 start；这样必填配置缺失时
仍可通过精确 schema 编辑配置。schema 可用不表示正在运行。启动完成后复核版本及
enabled；迟到实例必须清理。
冷启动只恢复已有启用的精确选择，不追 latest，也不把已撤回的 intent 写回 true。
停用、移除参与和进程退出保留共享 config/state 与 info-base 内容。

impl-rs 宿主周期性复核远端变化，停止已撤回的运行实例，并可启动已在本机安装的
新启用选择。相同版本启动失败后记录错误，不反复自动重启；显式 enable、观察到
停用或选择新版本可触发下一次尝试。running 只表示已完成启动且仍存活的本机进程，
不由 selection 或 enabled 推断。
