# Client Web Extension Runtime

`@inkcre/extension-runtime-client-web` 是独立发行的浏览器 Runtime。Host SDK `@inkcre/core` 拥有部署持久化模型、Peer 发现、传输和错误分类；Runtime 拥有 Extension 生命周期编排、管理命令消费和 Registry 发行读取。应用继续决定操作当前浏览器 Runtime、在线远端 Host，还是只改变部署中的 desired state。

`listAdvertisedExtensionManagementPeers()` 读取 `PeerManager.listLive()`，只保留宣告精确管理 capability 的 Peer。宣告不是协议支持、路由就绪或运行证明。`manageExtensionOnPeer(peerId, command)` 使用调用者指定的精确 Peer 和固定 capability，发送一次 install、enable、disable 或 patch_config 命令。它不替换目标、不重试、不改写 PeerManager 的传输失败分类；管理 HTTP 错误及无效业务响应不附带可能回显配置凭据的原始正文或校验详情。返回的安装记录仍不证明插件持续运行。

`getExtensionDocumentation(origin, name, version)` 使用调用者已解析的 Registry origin 和生成 HTTP 合同查询精确发行，只返回实际存在的 scope 与 entry_url。404 返回 null，成功但没有文档返回空数组；网络、其他 HTTP 错误、错误坐标和无效响应抛出 `RegistryDocumentationError`。调用者可以将不可用帮助入口降级为提示，不应据此阻止插件初始化。文档查询不执行安装预检，不要求 MF Distribution 或匹配的 Host SDK，不读取作者正文，也不回退到另一版本或 scope。

文档入口只接受无 URL 凭据的绝对 HTTP(S) 地址；UI 拥有外链展示、作者页面或锚点约定，以及断开 opener 的责任。公开发现请求不发送凭据。Registry 拥有文档托管与发行状态的具体合同，Runtime 不复制正文、内容域名构造或作者导航模型。

Runtime 的 Core peer dependency 以实际类型与构建验证为准，不使用 ambient SDK stub。新公共 API 通过 Changesets 声明 minor 发行意图，源包版本由正式版本流程修改。

Core SDK 尚未提供独立发布产物，因此开发依赖固定 client-web 的 Git revision；该子目录包只提供 manifest 和依赖，不能冒充构建产物。`prepare:sdk` 在临时目录只检出同一 revision 的 `packages/core`，沿用其真实源码、TypeScript 配置及原始 tsdown 配置，用 ext-reg 自身冻结的工具和 SDK 依赖构建 ESM 与类型声明，再将产物放入当前 workspace 的 node_modules 私有目录。它不安装生产者 workspace，不需要 GitHub Packages 凭据，也不改 pnpm store、生产依赖、源码或锁文件；首次构建只需读取公开 GitHub 源码。type-check 与 build 共用这一准备步骤，仓库门禁还通过真实 SDK 和本地 HTTP 运行 `check-boundaries.mjs`。正式 SDK 产物可用后，应改为固定产物开发依赖并删除准备脚本，而不是继续维护另一套 SDK 声明。
