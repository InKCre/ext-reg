# Registry Web 安装回跳

- **目标**：用户在 Registry Web 搜索、查看版本后，点“安装”返回 client-web 的 `/extensions`，由 client-web 按插件与精确版本确认并执行安装。
- **边界**：Registry 不接触部署凭据、不执行安装，也不引入 callback API 或新状态表。回跳 query 只承载插件名和版本；client-web 从自己的当前 Registry 配置重新读取 Release。浏览 client-web 的来源 origin 仅决定返回哪个 Web 站点，绝不作为安装身份。
- **完成证据**：无 JavaScript 的目录搜索→详情版本→回跳可用；来源 origin 与筛选、版本链接一起保留；无效来源不会生成任意跳转；Registry 检查及与 client-web 预览的实际往返通过。
- **当前事实**：Registry Web 已增加安装回跳和来源 origin 的逐页传递；回跳 query 只有 `install` 与 `version`，默认返回 `app.inkcre.dev`，无效来源返回 400。已在既有数据库/HTTP 验收脚本中增加回归断言。格式、lint、pyright、Web CSS、contracts、wheel 构建与包检查通过；本机无 `REGISTRY_TEST_DATABASE_URL`，故数据库验收须由隔离 CI 完成。Human 已授权与 client-web 一起修正并允许本仓库提交、推送、创建 draft PR。
- **下一步**：提交并推送 draft PR，观察隔离数据库 CI 与 Registry preview，随后联调 client-web。
