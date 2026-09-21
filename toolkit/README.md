# InKCre Extension Developer Toolkit

`inkcre-extension-toolkit` owns developer- and delivery-time Extension commands.
Install its `cli` extra through the repository's package manager to expose
`inkcre-ext`. The `preview build` command validates an explicit
language-neutral inventory and emits a deterministic static Registry projection
for supplied Python wheels and Module Federation snapshots.

The Toolkit is not a Registry service or a Host SDK. It does not own deployment
installation, Peer enablement, or runtime state.

Toolkit 0.3 提供 `inkcre-ext docs address/pack/publish/show`，用于独立静态文档的候选打包、条件发布和恢复。构建限制、完整 MIME 表和逐步命令见[静态文档发布协议](../docs/30-unit-tdd/documentation-admission.md)。
