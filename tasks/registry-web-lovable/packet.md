# Registry Web：Minimum Lovable Product

## 目标与授权

Sir 要求改善 Registry Web，可加入 Publisher；对齐 client-web 与 design，保持 Python 与单一部署流程。已授权独立分支/worktree、实现、提交、推送和 PR，不包含生产资源变更或合并。

2026-09-06 明确澄清：单一部署是避免 Vue/Vite CSR、Nuxt 等独立前端交付，已同意同一 Python Worker 的完整远程 PR 预览。

- 工作树：`.worktrees/registry-web/ext-reg`；分支 `feat/registry-web-lovable`；基线 `422a6cb`。
- 唯一任务控制入口为本 packet；原仓库分叉和其他任务内容保留。
- 配套组织约定工作树：`.worktrees/registry-web/governance`，分支 `feat/registry-worker-preview`，基线 `6d91c02`；仅更新 ext-reg 预览 profile 和适用的 Pages 专指。

## 当前实现与边界

- 产品已对齐 client-web：真实几何 logo、普通字号、直角边框、紧凑目录与详情；复用 design 已有公开 Sass package，无 hero、推广或持久教程面板。
- 目录支持搜索/发布者筛选；详情提供精确版本、原生分发和复制；Publisher 支持 Web 准备/上传/发布/撤回/恢复及私有分页，Python 上传沿用 Toolkit。
- From → To：静态 Pages 样张 → 每 PR 同一 Python Worker + 独立 D1/R2；删除静态生成器、carrier、fixture 和 Pages workflows。产品页面、控件和 URL 不含环境分支。
- 预览 workflow 自己使用现有构建命令；无凭据构建与有凭据部署在不同 runner。默认分支控制器验证成功 CI 与实时 PR head，只消费模块和迁移，生成完整绑定配置，不执行 candidate 部署命令。
- 更新保留该 PR 数据；关闭先替换写入入口，用原生 R2 binding 批量清空，再删 R2/Worker/D1。维护程序只存在于部署工具，不进入产品包。清理失败显式可见并可重试。
- 副作用仅为隔离预览资源、preview 环境专用测试发布凭据、配套治理约定。生产资源、custom domain、生产凭据、迁移结构和 shared 挂载均未修改。

## 验证与状态

- 完整 `pnpm check` 通过：样式新鲜度、合同、格式、lint、类型、wheel 和 Python Worker dry-run；本轮未修改产品源代码。
- 远程真实 Worker 已验证目录、详情、SemVer 默认/精确版本、Publisher 登录/准备、原生 ZIP 上传；控制器通过 API 创建 5 个可读 Web Releases，manifest publicPath 指向独立预览域名。
- 实际重复部署保留数据；带 R2 对象的完整清理已通过（Worker、D1、R2 同名 `inkcre-ext-reg-pr-33`）。重复清理也已通过；最终重建证据见部署日志与 PR 更新。
- 首次部署后一次 release GET 返回 500，后续日志未复现；未据此修改产品。部署验收增加 D1 公开读取就绪检查，再执行样例发布。
- 既往真实本地 Worker 已验证 Web/Python 发布、撤回恢复、私有分页与命名空间隔离。

## 交付与剩余启用条件

- 产品与预览：[ext-reg PR #33](https://github.com/InKCre/ext-reg/pull/33)。
- 组织交付约定：[.github PR #32](https://github.com/InKCre/.github/pull/32)。
- 完整远程 URL：`https://inkcre-ext-reg-pr-33.lanzhijiang.workers.dev`；最终提交部署后再交付。
- 已设置 preview 环境 `REGISTRY_PREVIEW_PUBLISHER_TOKEN`；原始凭据不进入日志、packet 或 PR。只有哈希写入隔离 D1。
- `CLOUDFLARE_PREVIEW_API_TOKEN` 尚未配置，已向 Sir 询问账户/凭据；不能复用生产 token。当前真实预览由本机已有 Wrangler 登录运行同一控制器完成。
- 已停用旧 Pages 两个 workflows，旧 PR #33 alias 转向完整 Worker；仅此 PR 开放中。
- 新 workflow_run 控制器须先进入 main 才会启用；不能从候选 PR 自行取得默认分支信任。未擅自合并。
- 长期设计：`docs/30-unit-tdd/registry-web.md`；预览运维：`docs/40-deployment/pull-request-previews.md`。PR 关闭前保留本 packet。
