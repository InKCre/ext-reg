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

## Typed 业务能力与撤销

`Descriptor.capabilities` 分别声明 Resolver、Storage、Source、Job 的精确身份与
schema。SDK 只拥有这些纯数据 DTO、固定 RPC 命令及作者 trait；impl-rs 拥有对应
runtime trait、registry 和持久 catalog。通用 `invoke` 不隐式发布任何业务能力。
空 capabilities 声明合法，便于只提供通用调用的扩展明确表达自己的范围。

Resolver 声明 hydrated content 的 text/bytes/json 契约、必要的直接关系方向、自定义
typed read 及可选 graph draft。宿主可在本地同步验证 canonical content；读取时按
声明获取实际内容与直接关系，再通过 resolver_read 发送明确的 solve/text/label/read
操作。文本 null、作者写入的空字符串、未知 decoder 和不支持投影分别保留含义。
resolver_draft 返回带临时 Block ID 的图数据，最终图完整性与持久事务仍归 Core。

Storage 负责不透明 pointer 与字节；writable 声明必须对应 create/update/delete。
Source 普通采集与 backfill 使用独立命令，不支持 backfill 时 schema 为 null。
Job 的参数 schema、默认 timeout 和领取前 eligibility 单独声明。Source/Job 返回的
state 是 Job.state 对象 patch；Source 自身的 state/cursor 通过已准入数据库维护，
不借启动快照覆盖其他参与者的新状态。字节及图结果仍遵守 1 MiB 帧边界，当前没有
跨进程大对象流式 API。外部 Storage 不能加入宿主传入的 PostgreSQL connection，
宿主图事务回滚不意味着外部字节已经回滚。

宿主在 start 成功并复核精确选择后注册能力，注册集合由该次启动的唯一 owner 标识。
停止、替换或部分启动失败只撤销这个 owner，不删除共享 catalog。注册 adapter 只持
Weak process handle；进程控制持有撤销信息，注册表不会通过引用环保留已关闭的进程。
协议错误或调用取消会同步撤销注册并终止子进程，正常停止先撤销注册再关闭进程。

RPC I/O 锁与进程控制分开。一个长采集不会占有整个 Host 状态锁，停用仍能立即
取消它。短 RPC 的期限包含等待协议锁与发送/接收，排队会消耗同一份预算；排队超时
尚未发送请求，只结束这个调用，不关闭正在执行其他工作的进程。Source/Job 没有
通用 20 秒期限；Worker 的执行预算、abort 与本机能力撤回
控制它们。执行 future 取消会 kill 实际进程，合作取消路径回收后才返回 Worker，
终态不能被当作外部副作用已回滚。同一进程中的其他调用可能受其结束影响；仅取消
尚未取得协议锁的排队工作不会结束正在执行的另一个工作。

宿主明确记录停止原因。Job 取消、执行预算到期或调用 future 取消触发的回收可以
按仍存在且启用的精确选择恢复新实例，不重新执行原 Job；崩溃、协议错误和初始化
失败保持错误，不重复自动启动同版本。这不依赖对子进程退出码的猜测。

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
