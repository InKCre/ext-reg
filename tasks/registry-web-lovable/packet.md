# Registry Web：Minimum Lovable Product

## 目标与授权

Sir 要求将 Registry Web 提升为可喜爱、可持续维护的产品，允许加入 Publisher 端；复用 ../design，保持 Python 与单一部署流程。已授权独立分支/worktree、实现、提交、推送和 PR；不包含生产资源变更或合并。

- 工作树：`.worktrees/registry-web/ext-reg`，分支 `feat/registry-web-lovable`，基线 `422a6cb`。
- 本 packet 是唯一任务控制入口；原仓库分叉及未提交内容保留。

## 当前纠正与边界

Sir 已认可修正后的产品视觉，但指出 preview/production 信息反过来塑造了产品实现。此判断已在模板、链接、样式和运行时预览函数中证实。

- 变更对象：Registry renderer、页面模板/CSS、独立静态证据生成器。From → To：产品内的环境开关/锚点导航/隐藏控件 → 同一套产品页面与原生 URL；静态样张在 scripts 层直接调用这些 renderer。
- 删除 `extension_preview_html`、产品 `preview.html`、预览专用 CSS 与仅为预览抽出的模板分层。目录、详情、复制、搜索、Publisher 和下载链接均不再因环境不同而改变。
- Pages 降为明确标注的不可交互页面样张：在产品外选择样张，样张内部保留原始控件和 URL。脚本负责 inert 容器、ID 命名空间、样例数据与体积上限；不进入 Worker 包。完整交互验收继续使用同一个真实 Python Worker 和隔离本地状态。
- 既有 Pages controller 仍可交付本 PR；更新后的 workflow 移除无效 api-origin 参数并正确描述证据范围，旧默认分支参数兼容仅留在 CLI 过渡层。
- 保留已认可的 client-web 视觉与真实 logo；发布 API、原生上传、数据库结构、Python 单 Worker 部署不变。无新增远程 Worker、权限、生产变更或 shared 编辑。

## 验收与状态

产品环境分支已删除；完整 `pnpm check` 通过，Worker dry-run 包含 503 个模块，wheel 中不含证据模板/生成器。实际 Worker 已验证搜索→详情→精确版本及 Publisher 入口，控制台无错误。独立样张保留正常产品 URL、具备唯一的元素 ID、inert 容器和独立键盘导航，生成体积约 52 KiB。

最终 CI 与 Pages 身份以 PR checks / preview.json 为准。本机真实 Worker 可在 `http://127.0.0.1:8791` 交互查看；其状态来自本任务隔离的本地 D1/R2，不是远程生产数据。

既往 Web/Python 发布、撤回恢复、私有分页及命名空间隔离证据保留；静态样张不再被描述为交互验收。

## 交付

- [PR #33](https://github.com/InKCre/ext-reg/pull/33)
- [Registry 预览](https://preview-ext-reg-pr-33.inkcre-extension-registry-ui-preview.pages.dev)
- 长期设计归属 `docs/30-unit-tdd/registry-web.md`；预览交付归属 `docs/40-deployment/pull-request-previews.md`。
- 回退整个 PR 恢复旧 Web 与读取合同，无数据回滚步骤。PR 未关闭前保留本 packet。
