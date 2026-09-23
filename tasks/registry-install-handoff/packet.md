# Registry Web 安装回跳

- **目标**：用户在 Registry Web 搜索、查看版本后，点“安装”返回 client-web 的 `/extensions`，由 client-web 按插件与精确版本确认并执行安装。
- **边界**：Registry 不接触部署凭据、不执行安装，也不引入 callback API 或新状态表。回跳 query 只承载插件名和版本；client-web 从自己的当前 Registry 配置重新读取 Release。浏览 client-web 的来源 origin 仅决定返回哪个 Web 站点，绝不作为安装身份。
- **完成证据**：无 JavaScript 的目录搜索→详情版本→回跳可用；来源 origin 与筛选、版本链接一起保留；无效来源不会生成任意跳转；Registry 检查及与 client-web 预览的实际往返通过。
- **当前事实**：Registry Web 已增加安装回跳和来源 origin 的逐页传递；回跳 query 只有 `install` 与 `version`，默认返回 `app.inkcre.dev`，无效来源返回 400。Draft PR [#56](https://github.com/InKCre/ext-reg/pull/56) 已推送；发布片段、HTML 属性转义均经 CI 修正，隔离 PostgreSQL 的完整 `ext-reg checks` 与 Dependency review 通过。client-web#118 的确认页在公开 preview + Human Heroku/Neon 部署完成 RSS 0.2.1 安装、刷新和卸载验收。
- **预览事实**：Registry #56 的隔离 CPython Web 预览已部署到 `https://inkcre-ext-reg-pr-56-bcb9e238282c.herokuapp.com/`，`/livez` 报告的 revision 是 PR head `d58bdcb34f73840b413c3db0c147587d10bf955f`。独立 Neon 分支为空，目录没有 Release，因此尚未完成从 Registry 版本页点击到 client-web 的跨站验收。保持 PR 为 Draft，不把 client-web 手工构造的回跳链接当成完整跨站证据。
- **预览关联修正**：此前 `workflow_run` 的 `environment: preview` 把自动 GitHub Deployment 记在默认分支 `main`，导致 #56 的 PR Checks 没有预览入口。现在交付及清理 job 保留 preview 环境密钥和分支规则，但禁用自动 Deployment；交付在重新核对 PR head 后显式创建该 SHA 的 Deployment 与 `ext-reg preview` commit status，报告实际 URL/失败；清理在资源删除成功后将此 PR 的 Deployment 标为 inactive。工作流在合入 `main` 前仍由旧版可信控制器运行，实际 GitHub 关联须在合入后用新 PR 运行验证。
- **跨仓库审计**：`client-web` 与 `core-py` 的近期 preview Deployment 已关联 PR head；`docs` 的 `main` 仍在 `workflow_run` 自动生成 main Deployment，#31 有显式 PR-head Deployment，本轮在 #31 补回 `preview` environment 并禁用其自动 Deployment；`ui` 的 `workflow_run` preview 亦存在 main Deployment（例如 `6607896895` 指向 PR #53 预览），尚未改其交付流程。`.github/GOVERNANCE.md` 的“预览 job 声明 preview 环境”原则正确，但 ext-reg 静态 Pages 预览描述过时，且未区分 controller SHA 与候选 SHA；没有证据说明该文档造成这些错误。
