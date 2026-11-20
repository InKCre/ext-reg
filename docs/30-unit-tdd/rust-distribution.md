# Rust executable 分发

发布与消费 Rust 原生插件时阅读本文。`rust_stdio` 是独立的 native Distribution，与 Python、Module Federation 使用相同 Extension Name，并分别拥有版本发布状态。一个版本声明所有目标 triple；target 选择执行平台，持久业务身份仍由 Extension Name 拥有。

发布者先用 namespace credential 调用 `POST /v2/extensions/{namespace}/{name}/distributions/rust_stdio/releases`。请求包含 nickname、version 和 rust_stdio association。association 保存 core-rs SDK 范围、源码仓库与 revision、可选 build_id，以及非空唯一 targets。支持 Apple Darwin 的 aarch64/x86_64、GNU Linux 的 aarch64/x86_64、Windows MSVC x86_64。准备后这些字段不可替换。

每个 target 通过 `POST /v2/extensions/{namespace}/{name}/distributions/rust_stdio/releases/{version}/artifacts/{target}` 上传原始 executable。单文件上限128 MiB，服务器计算 SHA-256，并以内容寻址存储。同 target 的相同 bytes 可以在 preparing 状态重复上传；不同 bytes 会返回409。所有声明 target 完整存储后，才可调用同版本的 `/publish`。

精确公开版本的 rust_stdio 字段包含 host_sdk、host_sdk_version、protocol_version，以及 artifacts 数组。每项具有 target、executable_url、sha256、size。executable_url 是同 Registry origin 下的相对路径。Host 按目标平台选择，检查 SDK 范围、协议、字节数与摘要，然后构造本机可信 manifest，并通过实际 initialize 握手检查业务身份。

Registry 托管发布者提供的原生代码。构建、目标平台真实性及签名策略由发布者承担。下载入口遵循现有 published/yanked 精确版本策略，blocked 内容不可读。Registry 不执行上传文件。对象上传在事务外完成，最终 association 在 release 行锁下提交，并发发布会使后来的上传明确失败。未引用的内容寻址对象可由既有存储维护流程回收。

本次 migration 为 NativeRelease 增加一个 Rust snapshot，沿用既有行锁及发布快照比较。历史 CreateModel 在部分 Tortoise 版本中未真正创建模型序列化的约束，新增 migration 在调整 distribution check 之前兼容这两种已部署形态。
