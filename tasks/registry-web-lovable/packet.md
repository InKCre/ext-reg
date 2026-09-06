# Registry Web：Minimum Lovable Product

## 目标与授权

Sir 要求改善 Registry Web，可加入 Publisher；对齐 client-web 与 design，保持 Python 与单一部署流程。已授权独立分支/worktree、实现、提交、推送和 PR，不包含生产资源变更或合并。

已明确单一部署是避免 Vue/Vite CSR、Nuxt 等独立前端交付，同意同一 Python Worker 的完整远程 PR 预览。后续数据库复制与额外迁移治理方案已被 Sir 否决，不实施。

- 工作树：`.worktrees/registry-web/ext-reg`；分支 `feat/registry-web-lovable`；基线 `422a6cb`。
- 唯一任务控制入口为本 packet；原仓库分叉和其他任务内容保留。
- 配套治理工作树：`.worktrees/registry-web/governance`；分支 `feat/registry-worker-preview`；仅调整组织 ext-reg 预览交付约定。

## 当前实现

- 产品对齐 client-web：真实几何 logo、普通字号、直角边框、紧凑目录与详情；复用 design 已有公开 Sass package，无 hero、推广或持久教程面板。
- 目录支持搜索/发布者筛选；详情提供精确版本、原生分发和复制；Publisher 支持 Web 准备/上传/发布/撤回/恢复及私有分页，Python 上传沿用 Toolkit。
- 每 PR 使用同一 Python Worker + 独立 D1/R2；静态 Pages 样张已移除。产品页面、控件和 URL 不含环境分支。
- 预览 workflow 自己使用现有构建命令；无凭据构建与可信部署控制器分处不同 runner。控制器验证成功 CI、实时 PR head 并生成完整绑定配置。
- 更新保留该 PR 数据，关闭时清理对应 Worker/D1/R2；维护程序不进入产品包。

## 已批准并实施的 demo 修正

- From → To：部署自动创建样例 Releases → 部署只配置资源和 Publisher 登录，匿名读取检查支持空目录。删除 seed、样例构造代码、样例详情/manifest 专用检查，共移除脚本 66 行；未新增机制或产品修改。
- 已核对并清理 PR #33 中 demo/github 的 1.0.0、1.10.0、2.0.0-rc.1，以及 demo/memos、demo/rss、demo/notes 各 1.0.0；共 4 个扩展、6 个版本、12 个精确 R2 对象。
- 清理前核对 source_repository/source_revision、snapshot hash 和 asset paths；只删除上述记录及对应 keys，不重置数据库。数据库 UUID `7d67ae5e-c0b3-4fca-841c-4c4c7661dd73` 未变；命名空间、凭据和迁移记录数保持不变，外键检查通过。
- Publisher 登录配置独立保留；没有扩展时使用现有空态，实际需要验收的扩展由 Publisher/Toolkit 上传。临时验收数据不再作为常驻预览数据。

## 验证与交付

- 本轮完整 `pnpm check` 通过；远程目录已为空，旧 demo 详情返回 404，Publisher 仍可登录且 release 列表为空。最终提交重部署及 CI 结果记录于 PR。
- 既往真实 Worker 已验证详情/版本、Web/Python 发布、撤回恢复、私有分页、命名空间隔离、重复部署和带对象清理；验收数据现已删除。
- [ext-reg PR #33](https://github.com/InKCre/ext-reg/pull/33)；[配套 .github PR #32](https://github.com/InKCre/.github/pull/32)。
- [完整预览](https://inkcre-ext-reg-pr-33.lanzhijiang.workers.dev/)；旧 Pages alias 已转向此 URL，旧 Pages workflows 已停用。
- GitHub preview 环境已配置 `REGISTRY_PREVIEW_PUBLISHER_TOKEN`；`CLOUDFLARE_PREVIEW_API_TOKEN` 尚未配置。当前远程预览由本机已有 Wrangler 登录运行同一控制器部署。新控制器须先进入 main 才能自动触发；未擅自合并或修改生产资源。
- 长期设计：`docs/30-unit-tdd/registry-web.md`；预览运维：`docs/40-deployment/pull-request-previews.md`。PR 关闭前保留本 packet。
