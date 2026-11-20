# Rust executable Extension SDK

编写 Rust 扩展或为原生 Peer 实现宿主时阅读本文。`runtimes/core-rs` 的
`inkcre-extension-sdk` 是独立 Cargo crate，拥有 `rust_stdio` 本地分发格式、
版本化消息、扩展 trait 和 stdio runner，不依赖 Registry 服务或任一 Core 实现。
业务、共享信息和 Peer 参与语义继续由 Hub 契约拥有。

扩展是可信本地 executable，以独立子进程加载；宿主 HTTP app 自身仍可作为单个二进制分发。
进程隔离用于明确加载、更新与回收边界，不构成恶意代码 sandbox。SDK 不使用 Rust 动态库 ABI。

## 分发边界

操作者可以显式提供本地 manifest 和 executable，或按 [Rust 原生分发](rust-distribution.md)
下载 Registry 精确发布版本。Registry 托管发布者的原生 bytes 与摘要，不执行文件或
承诺源码/平台真实性。Rust SDK 采用自身 Cargo 版本，原生安装 manifest 标识
精确 Extension name/version、宿主 SDK 条件、协议版本和 executable SHA-256。

manifest 数据结构和严格输入规则由 SDK `Manifest` 及 `validate` 拥有。
executable 是 manifest 目录内相对路径；宿主复制产物到自己的不可覆盖精确坐标目录，
校验复制后的摘要，再保存当前 Peer 的 selection。后续启动重新验证摘要与坐标。
更新需要新版本；保持旧进程运行时不能更换其精确 selection。

## 运行协议

stdin/stdout 使用 UTF-8 JSON-line，普通帧（包含换行）最多 1 MiB。已协商的
HTTP ingress 使用下文独立限制。SDK 读取时逐块
检查边界，不先无界读入；stdout 只输出协议，日志写 stderr。请求包含
`protocol_version`、`id`、`method`、`params`。响应返回相同版本与 ID，并恰有
`result` 或 `error`；成功结果可为 JSON null。协议 v1 按顺序请求/响应。宿主可以协商
同一次请求内的 Storage 回调。多路复用和任意 SQL RPC 不属于此协议。

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
不借启动快照覆盖其他参与者的新状态。普通业务结果遵守 1 MiB 帧边界。已协商的
Storage/Resolver 二进制值单个最多 32 MiB，帧最多 48 MiB。

`storage.v1` 回调可借用当前 Peer 的 Storage handler，使用持久 Storage ID 与 opaque
pointer。协商 `resolver.storage.materialization.v1` 后，活动 Resolver 的 Solve/Text
仅在 `materialize_missing=true` 时可借用 Create，其他 Resolver 调用只可借用 Read。
调用端应优先采用能加入当前 PostgreSQL 事务的本地 Storage。借用外部 handler 的创建
独立提交；后续图事务失败时，调用者负责处理已创建对象的生命周期。

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

## HTTP ingress

这是一条已安装扩展的本机访问协议，不是 `core.peer.protocol.http.v1` 的 Peer
委派传输。SDK 只拥有 stdio 上的 typed bytes、路由 admission 与分派；HTTP server、
Peer JWT、实际 mount 以及 Peer capability advertisement 由 Host 拥有，外部协议的
凭证验证由插件拥有。普通扩展 route 默认使用 Peer JWT。协议根的 auth-neutral
边界通过每条 `auth=protocol/public` 的显式声明表达，不会从方法名或 URL 猜测。

`Descriptor.capabilities.http_ingress` 是可选对象：

```json
{
  "routes": [
    { "method": "GET", "path": "/memos/connection", "path_match": "exact", "auth": "peer" },
    { "method": "POST", "path": "/memos/api/v1", "path_match": "prefix", "auth": "protocol" }
  ],
  "peer_inbounds": [
    { "capability": "memos.connection.v1", "method": "GET", "path": "/memos/connection" }
  ]
}
```

method 使用有界 RFC HTTP token，保持大小写，不以 GET/POST 白名单排除 DAV 方法。
path_match 默认 exact，prefix 匹配路径本身或随后带 `/` 的后代，不能把 `/memosx`
当作 `/memos`。exact 优先，其次最长 prefix；相同 method/path/path_match 声明
不可重复。auth 默认 peer；protocol 要求插件实际验证其协议凭证；public 表示明确
公开的结果。Peer inbound 只能精确引用一条 peer/exact route，不允许通过 protocol
或 public 路径发布部署 Peer capability。

Host 和 runner 都调用 `validate_mount(descriptor.name)`。canonical Extension Name
`namespace/name` 只可声明 `/name` 及其后代；不同 namespace 的同名 mount 必须由
Host 在发布前检查冲突。生命周期 start 完成且精确选择仍有效后才挂载，停用、失败、
替换或进程退出时撤销同一次启动拥有的 route 与 inbound，不能留悬空转发入口。

path 是 Host 从 URI 解码一次得到的 Unicode 绝对路径。共享验证拒绝 `%`、`.`/`..`
段、双斜杠、反斜杠、控制字符、query 或 fragment，避免 Host、路由器与插件采用
不同解码次数造成认证绕过。有百分号字面量的路径也明确拒绝。admission 后不可
二次解码、折叠路径或改写到另一个 route。query 字段另行保留原始 query string，
不含前导 `?`。Host 必须在解码失败或出现歧义时拒绝请求。

固定命令 `http_request` 的 params 字段为 method/path/query/headers/body；result
字段为 status/headers/body。`HttpHeader` 是 `{name,value}`，name 必须为小写 RFC
header token，value 是 JSON bytes 数组，重复字段保留顺序；总 decoded header 上限
64 KiB、最多 256 项，拒绝控制字符（HTAB 除外）。Host 剔除 hop-by-hop 和 framing
字段，不能把未经核验的转发地址或内部认证标记当作 authority。

`HttpBody(Vec<u8>)` 的 JSON 编码为标准 padded Base64 string，反序列化与序列化
都验证 decoded body 不超过 45 MiB；这是 HTTP bytes 上限，产品内的 JSON base64
等编码仍属于 HTTP bytes。Memos 的 32 MiB decoded attachment 可具有45 MiB的HTTP
request envelope；CalDAV仍由插件执行16 MiB请求限制。query 上限64 KiB、path上限
8192 bytes。status为200..599；没有长连接、HTTP upgrade或流式响应。

SDK 的 read_frame/write_frame 保留默认 1 MiB；显式
read_frame_with_limit/write_frame_with_limit 支持 Host 按调用方法选界限。
runner 只在已启动且声明了 http_ingress 时把读取上限提高为64 MiB，只有
http_request 可使用这个额度；解析后发现普通命令超过1 MiB会返回frame_size。
HTTP响应最多64 MiB，其他响应仍为1 MiB；45 MiB body编码后约60 MiB，保留元数据
余量。initialize、start和未声明HTTP的旧插件始终使用原限制。

外层 stdio protocol_version 仍为1：这是 optional typed capability 的新增，不更改
旧帧字段。None 的 http_ingress 不序列化，新 SDK 的普通扩展可与旧 Host 互通；
旧插件省略字段时，新 Host 读取为 None。声明HTTP的扩展对不认识该字段的旧Host
会明确握手失败，不能退化为未经准入的通用 invoke 或绕过认证。Host 应使用SDK类型
解析与验证 HTTP result，不能把任意 JSON 转成 server response。
