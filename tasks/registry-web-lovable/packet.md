# Registry Web：Minimum Lovable Product

## 目标与授权

Sir 要求将 Registry Web 提升为可喜爱、可持续维护的产品，允许加入 Publisher 端；复用 ../design，保持 Python 与单一部署流程。已授权独立分支/worktree、实现、提交、推送和 PR；不包含生产资源变更或合并。

- 工作树：`.worktrees/registry-web/ext-reg`，分支 `feat/registry-web-lovable`，基线 `422a6cb`。
- 本 packet 是唯一任务控制入口；原仓库分叉及未提交内容保留。

## 方案与边界

- 静态名称列表 → Python/Jinja 服务端目录、搜索/发布者筛选、版本详情和 Publisher 工作台。
- 直接消费已发布的 `@inkcre/ui-web` Sass 公共接口，构建 CSS 随 Python 包/Worker 交付。无独立前端服务。
- Publisher 复用 namespace bearer 凭证与既有 prepare/upload/publish/yank/unyank 协议；增加自己的私有版本读取接口。浏览器支持 Module Federation ZIP 发布，Python 原生发布仍交给现有 Toolkit。
- 不改变 Release/installed/enabled/running 权威，不改变公共 API 既有语义，不修改 D1 schema。
- 资产/边界：发布者凭证授予命名空间写权限；公开昵称是外部数据。模板自动转义、浏览器 textContent、同源请求、仅内存凭证避免将公开元数据变成脚本或凭证泄露路径。依据 Hub security-boundary-model 和本地 registry-control-plane。
- 静态 Pages preview 保持无凭证、只读目录性质；卡片指向已上线的 API 元数据，Publish 指向 Toolkit 文档，不声称运行候选 API。

## 验收与当前进度

1. 完成目录、详情、Publisher 浏览器流程，空态、失败态、移动端和键盘可用。
2. 真正消费 design 样式，检查浅/深色与窄屏页面。
3. 完整 `pnpm check`、Worker 本地 D1/R2 黑盒验证、构建包包含模板/资源、`git diff --check`。
4. 更新拥有长期事实的本地文档，提交推送 PR，观察 CI 并修复本次失败。

当前：实现与本地验收完成；[PR #33](https://github.com/InKCre/ext-reg/pull/33) 已提交，CI 与 Pages preview 在 `29d5686` 均通过。主题、分页反馈、模板可读性和预览链接修正已纳入交付；最终提交的自动化结果以 PR checks 与 preview.json 的 source_sha 为准。暂无需 Sir 决策项。

## 验收证据与交付

- Node 22 下完整 `pnpm check` 通过，包含合同生成、格式、lint、类型、各 wheel/客户端构建、Worker dry-run；确认模板、CSS、JS 与 Jinja 运行依赖进入 Worker。
- 使用本地 Worker 和隔离的 D1/R2：匿名 Publisher 401/no-store、自身命名空间分页、其他命名空间不可读取/修改；真实 Web prepare/upload/publish 和 Python 原生 wheel 上传、发布、详情均通过。
- 浏览器完成 Web 新建（含错误修正与字段保留）、ZIP 上传、发布、撤回、恢复、断开凭证；未上传版本不可发布。从第二页新建后回到第一页并展示新版本。
- 验证目录搜索、空态、精确版本选择、SemVer 稳定版优先、详情 404、ID 复制、390px 窄屏无水平溢出、浅/深色与控制台；公开昵称自动转义。
- 首次 CI 暴露 GitHub Packages 403；改用 pnpm 原生 Git 子目录依赖，锁定 design 已发布 1.4.0 的公共提交 `4eceec4c60345a52a08545555ebce9ab95053beb`。Sass 产物一致，无需扩大包权限或新增发布流程。
- 长期设计归属 `docs/30-unit-tdd/registry-web.md`；构建/预览归属 `docs/40-deployment/`。无 shared 文档、数据库 schema 或生产资源变更。
- [目录视觉预览](https://preview-ext-reg-pr-33.inkcre-extension-registry-ui-preview.pages.dev) 复用现有 Pages 流程；发布者交互在真实本地 Worker 验收。Python prepare/upload 仍由现有 Toolkit 执行，网页负责发布与生命周期管理。
- 回退整个 PR 恢复旧 Web 与读取合同，无数据回滚步骤。PR 未关闭前保留本 packet。
