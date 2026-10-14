# Client Web Extension Runtime

`@inkcre/extension-runtime-client-web` 是独立发行的浏览器 Runtime。Host SDK `@inkcre/core` 拥有部署持久化模型、Peer 发现、传输和错误分类；Runtime 拥有 Extension 生命周期编排、管理命令消费和 Registry 发行读取。应用继续决定操作当前浏览器 Runtime、在线远端 Host，还是只改变部署中的 desired state。

`listAdvertisedExtensionManagementPeers()` 读取 `PeerManager.listLive()`，只保留宣告精确管理 capability 的 Peer。宣告不是协议支持、路由就绪或运行证明。`manageExtensionOnPeer(peerId, command)` 使用调用者指定的精确 Peer 和固定 capability，发送一次 select、enable、disable 或 patch_config 命令。它不替换目标、不重试、不改写 PeerManager 的传输失败分类；管理 HTTP 错误及无效业务响应不附带可能回显配置凭据的原始正文或校验详情。返回的运行投影区分持久化选择与实际加载结果。

`getExtensionDocumentation(origin, name, version)` 使用调用者已解析的 Registry origin 和生成 HTTP 合同查询精确发行，只返回实际存在的 scope 与 entry_url。404 返回 null，成功但没有文档返回空数组；网络、其他 HTTP 错误、错误坐标和无效响应抛出 `RegistryDocumentationError`。调用者可以将不可用帮助入口降级为提示，不应据此阻止插件初始化。文档查询不执行安装预检，不要求 MF Distribution 或匹配的 Host SDK，不读取作者正文，也不回退到另一版本或 scope。

文档入口只接受无 URL 凭据的绝对 HTTP(S) 地址；UI 拥有外链展示、作者页面或锚点约定，以及断开 opener 的责任。公开发现请求不发送凭据。Registry 拥有文档托管与发行状态的具体合同，Runtime 不复制正文、内容域名构造或作者导航模型。

Runtime 的 Core peer dependency 以实际类型与构建验证为准，不使用 ambient SDK stub。新公共 API 通过 Changesets 声明 minor 发行意图，源包版本由正式版本流程修改。

Core SDK 开发依赖固定官方 `core-v0.4.0` GitHub Release 的预构建 tgz，冻结锁文件验证下载完整性。该产物同时包含 ESM 和类型声明，type-check 与 build 直接消费它，不检出 client-web 源码、不安装生产者 workspace，也不需要私有 UI 包凭据。仓库门禁通过真实 SDK 和本地 HTTP 运行 `check-boundaries.mjs`；正式 Runtime 包由本仓独立版本流程发布，Core 的 peer dependency 继续声明兼容范围。

Runtime 使用 Registry v2 原生坐标查询 MF，公开 catalog 可明确选择 distribution；返回坐标和唯一原生关联均须匹配。安装将共享 Extension 身份与当前 Peer 的精确参与选择分别保存，enable/startup 读取当前 Peer 选择，不追随 latest，不修改其他 Peer 或清理业务 state。旧未知分发仅用当前浏览器支持的 MF 查询同一精确版本，缺失时失败而不替换版本。

管理能力为 `core.extension.management.v2`。`select` 明确指定分发与版本，`status` 返回目标 Peer 的能力和实际运行事实；所有响应采用 `{peer_id,supported_distributions,extensions}`，逐行包含精确选择和实际 loaded_version/running。Runtime SDK 校验目标身份与每行身份，保留原 PeerManager 的传输失败分类，不能由持久化 enabled 推断正在运行。删除参与记录保留部署配置和业务 state。

显式 enable/disable 先按同一 Host、同一 Extension 的命令顺序保存 enabled 意图，再串行执行模块生命周期。disable 在等待在途启动之前保存 false，并在资源清理完成后返回。startup 只恢复已有意图，成功或失败都不反写 enabled；初始化失败保留意图及错误，允许后续恢复重试。

恢复在加载前及异步 initialize/activate 后重新读取精确参与选择。若 enabled 被撤回、分发或版本改变，迟到的模块会执行 dispose，不能登记为 running。shutdown 等待在途恢复与命令完成并清理模块。同 Host 的串行队列不锁住其他已准入客户端对共享数据库的写入，因此离线意图更新不等于瞬时、原子的进程切换；这些客户端的修改通过重新读取被识别。
