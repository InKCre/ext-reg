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
- 静态 Pages preview 保持无凭证、只读目录性质；详情/发布指向生产，不声称运行候选 API。

## 验收与当前进度

1. 完成目录、详情、Publisher 浏览器流程，空态、失败态、移动端和键盘可用。
2. 真正消费 design 样式，检查浅/深色与窄屏页面。
3. 完整 `pnpm check`、Worker 本地 D1/R2 黑盒验证、构建包包含模板/资源、`git diff --check`。
4. 更新拥有长期事实的本地文档，提交推送 PR，观察 CI 并修复本次失败。

当前：已完成仓库/设计/治理/原生协议调查，正在安装依赖并实现。待验证 Jinja 打包与 Worker 运行，GitHub Packages CI 读取权限。暂无需 Sir 决策项。
