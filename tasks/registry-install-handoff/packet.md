# Registry Web 安装回跳

- **目标**：用户在 Registry Web 搜索、查看版本后，点“安装”返回 client-web 的 `/extensions`，由 client-web 按插件与精确版本确认并执行安装。
- **边界**：Registry 不接触部署凭据、不执行安装，也不引入 callback API 或新状态表。回跳 query 只承载插件名和版本；client-web 从自己的当前 Registry 配置重新读取 Release。浏览 client-web 的来源 origin 仅决定返回哪个 Web 站点，绝不作为安装身份。
- **完成证据**：无 JavaScript 的目录搜索→详情版本→回跳可用；来源 origin 与筛选、版本链接一起保留；无效来源不会生成任意跳转；Registry 检查及与 client-web 预览的实际往返通过。
- **当前事实**：Registry Web 已增加安装回跳和来源 origin 的逐页传递；回跳 query 只有 `install` 与 `version`，默认返回 `app.inkcre.dev`，无效来源返回 400。Draft PR [#56](https://github.com/InKCre/ext-reg/pull/56) 已推送；发布片段、HTML 属性转义均经 CI 修正，隔离 PostgreSQL 的完整 `ext-reg checks` 与 Dependency review 通过。client-web#118 的确认页在公开 preview + Human Heroku/Neon 部署完成 RSS 0.2.1 安装、刷新和卸载验收。
- **下一步**：Registry #56 尚未部署；从 Registry Web 版本页实际点击回跳的跨站往返仍须在其可用环境验收。保持 PR 为 Draft，不把 client-web 手工构造的回跳链接当成完整跨站证据。
