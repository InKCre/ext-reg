# Registry Web：Minimum Lovable Product

## 目标与授权

Sir 要求将 Registry Web 提升为可喜爱、可持续维护的产品，允许加入 Publisher 端；复用 ../design，保持 Python 与单一部署流程。已授权独立分支/worktree、实现、提交、推送和 PR；不包含生产资源变更或合并。

- 工作树：`.worktrees/registry-web/ext-reg`，分支 `feat/registry-web-lovable`，基线 `422a6cb`。
- 本 packet 是唯一任务控制入口；原仓库分叉及未提交内容保留。

## 当前纠正与边界

Sir 指出上一版偏离产品风格、增加过多 hero/tips/notices 且 logo 错误，预览看不到详情。此前 minimum 判断作废，以 `client-web` 的实际产品语言为准。

- 参照 `client-web/apps/client-web/src/App.vue`、extensionCard、design InkHeader/InkButton：32px 官方几何 logo、普通字号、直角边框、紧凑列表、白色工作区。删除宣传 hero、装饰图、假 logo、重复提示和页脚 CTA。
- 变更对象：Registry 模板/CSS 和预览生成器。From → To：营销目录 → 简洁产品界面；只读目录/API 跳转 → 同一文档内的目录、详情、版本切换与返回。
- 继续消费 design 已发布 Sass 公共接口，保留 Python/Jinja 与单 Worker；logo 精确来自 client-web 的 public/logo/32.svg。发布 API、原生上传协议、D1/R2 语义不变。
- Pages 的现有默认分支 controller 只交付 index.html 且禁止脚本。预览复用生产详情模板和显式样例 release，通过锚点和 CSS 显示当前详情；保持 64 KiB 文档上限，无新增预览服务、权限或部署流程。页头用 Preview 标识样例数据；不向线上 API 导航假版本。
- 本轮不编辑 client-web、design、shared 文档或生产资源。沿用已授权的同一 PR 提交/推送。

## 验收与状态

修正已完成，完整 `pnpm check` 通过（含 Worker dry-run 的 506 个模块与全部新模板）。浏览器验证目录→详情→版本→返回、实际 Worker 搜索→Python 详情、复制 ID、深浅色、发布者连接/新建表单/Escape/断开；390px 页面无横向溢出，控制台无错误。

最终静态预览保留 64 KiB 上限；已检查所有锚点存在且唯一、不包含脚本。logo 与 client-web 源 SVG 比对一致。最终提交的 CI、预览交付状态和 source_sha 以 PR checks / preview.json 为准。

上一轮的 Web/Python 发布、撤回恢复、私有命名空间分页和隔离验证仍是后端证据；不作为本轮视觉验收依据。

## 交付

- [PR #33](https://github.com/InKCre/ext-reg/pull/33)
- [Registry 预览](https://preview-ext-reg-pr-33.inkcre-extension-registry-ui-preview.pages.dev)
- 长期设计归属 `docs/30-unit-tdd/registry-web.md`；预览交付归属 `docs/40-deployment/pull-request-previews.md`。
- 回退整个 PR 恢复旧 Web 与读取合同，无数据回滚步骤。PR 未关闭前保留本 packet。
