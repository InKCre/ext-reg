---
'@inkcre/extension-runtime-web': patch
---

将浏览器 Extension Runtime 更名为 `@inkcre/extension-runtime-web`，目录、构建及独立发布产物使用 Web App 命名；公开运行时 API 和已发布旧名称产物保持兼容。

同时将 Runtime 的直接 Zod 依赖升级到 4.6.6，修复超大集合验证导致内存耗尽的问题（GHSA-mrhx-c7xc-m3w5）。
