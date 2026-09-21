# 静态文档发布协议

本文面向 Extension 文档作者。Registry 托管作者已构建的静态资源，不运行 SSG，也不解释 Markdown、导航或搜索结构。全局文档使用 `global`，渠道文档使用 `python` 或 `module-federation`；每组文档属于一个精确 Extension Release，渠道组要求该 Release 已关联对应 Distribution。

## 构建与准入

将站点构建为一个输出目录，默认入口为 `index.html`。站点在独立快照 origin 的根目录运行，可以使用根相对资源地址。Registry 不执行作者的服务器配置。以下限制是作者可依赖的准入合同；修改限制或删除已准入的类型时，必须评估现有构建的兼容性并记录变更。

| 项目       | 准入要求                                                                                                             |
| ---------- | -------------------------------------------------------------------------------------------------------------------- |
| 请求大小   | 整个 multipart 请求（包括 metadata、边界和 ZIP）不超过 20 MiB，必须有 `Content-Length`，不接受 chunked 上传          |
| ZIP 大小   | ZIP 本身不超过 20 MiB；临近上限时须为 multipart 开销留空间                                                           |
| 展开大小   | 所有文件合计不超过 100 MiB，单文件不超过 20 MiB                                                                      |
| 成员数量   | 最多 4096 个 ZIP 成员，显式目录也计入；Toolkit 打包仅写文件成员                                                      |
| 压缩比     | 单文件超过 1 MiB 时，展开大小不得超过 `200 × max(压缩大小, 1)`                                                       |
| 入口       | 已存在的、以小写 `.html` 结尾的文件；通过 `--entry` 可选择其他路径                                                   |
| 路径       | 相对、规范化的 POSIX 路径，UTF-8 编码不超过 768 字节；禁止空路径、绝对路径、重复斜线、`.`/`..` 和任何以 `.` 开头的段 |
| 路径字符   | 禁止反斜线、`%`、`?`、`#`、`:`、ASCII 控制字符及 DEL                                                                 |
| 服务器配置 | 任意路径段不得为 `_headers` 或 `_redirects`                                                                          |
| 文件结构   | 只接受普通文件和目录，禁止 symlink、其他特殊成员、加密成员、重复路径和文件/目录冲突                                  |
| 文件类型   | 必须具有下表中的小写扩展名；MIME 由 Registry 决定，不采用上传方声明                                                  |

| 扩展名            | 响应 MIME                           |
| ----------------- | ----------------------------------- |
| `.html`           | `text/html`                         |
| `.css`            | `text/css`                          |
| `.js`, `.mjs`     | `text/javascript`                   |
| `.json`, `.map`   | `application/json`                  |
| `.txt`            | `text/plain`                        |
| `.xml`            | `application/xml`                   |
| `.svg`            | `image/svg+xml`                     |
| `.png`            | `image/png`                         |
| `.jpg`, `.jpeg`   | `image/jpeg`                        |
| `.gif`            | `image/gif`                         |
| `.webp`           | `image/webp`                        |
| `.avif`           | `image/avif`                        |
| `.ico`            | `image/x-icon`                      |
| `.woff`, `.woff2` | `font/woff`, `font/woff2`，分别对应 |
| `.ttf`, `.otf`    | `font/ttf`, `font/otf`，分别对应    |
| `.pdf`            | `application/pdf`                   |
| `.wasm`           | `application/wasm`                  |
| `.webmanifest`    | `application/manifest+json`         |
| `.mp3`            | `audio/mpeg`                        |
| `.mp4`            | `video/mp4`                         |
| `.webm`           | `video/webm`                        |
| `.ogg`            | `audio/ogg`                         |

路由按“精确文件 → 目录内 `index.html` → 同名 `.html`”查找；目录缺少结尾斜线时重定向补齐。根路径返回指定入口。没有 SPA fallback，不存在的路径返回 404；SSG 应输出实际页面文件。

## 用 Toolkit 发布

使用 Toolkit 0.3.x 的 `cli` extra。先用自己的 SSG 生成输出目录，再保存候选：

```bash
inkcre-ext docs pack --site ./site-output --output ./docs-candidate \
  --name example/my-extension --version 1.0.0 --scope global \
  --source-repository https://github.com/example/my-extension \
  --source-revision COMMIT_SHA
```

`pack` 会执行与 Registry 相同的静态资源检查，并保存 ZIP、metadata、随机快照 ID 和写入前提。输出目录必须尚不存在。如果 SSG 需要绝对 origin，先运行 `inkcre-ext docs address --registry-url REGISTRY_URL`，将返回的 origin 用于构建，并将该 `snapshot_id` 传给 `pack --snapshot-id`。这只是生成未绑定地址；实际占用和冲突检查发生在发布时。

将发布凭据通过 `INKCRE_EXTENSION_REGISTRY_TOKEN` 环境变量提供，随后提交已保存候选：

```bash
inkcre-ext docs publish --registry-url REGISTRY_URL --candidate ./docs-candidate
inkcre-ext docs show --registry-url REGISTRY_URL \
  --name example/my-extension --version 1.0.0
```

首次发布使用 `If-None-Match: *`。修订时先通过 `show` 读取对应 scope 的 ETag，审核当前内容，然后将完整的带引号 ETag 传给新候选的 `pack --if-match '"ETAG"'`。尚处于 preparing 的 Release 使用 `show --private`；文档可以准备，但在 Release 发布前不可公开阅读。

每次修订必须生成新快照 ID。请求超时或响应丢失时，重试原候选，保留原 ZIP、metadata 和 precondition；Toolkit 回读并核对完整身份。412 表示当前指针与观察值不符，应重新阅读并由作者决定如何修订，不能自动采用新 ETag 覆盖。旧快照继续服从其所属 Release 的生命周期：yanked 仍可读，blocked 拒绝包括历史快照在内的新网络读取。

## 直接使用 HTTP

[JSON Schema](../../contracts/documentation.schema.json) 定义 upload、release 和 hosting；[OpenAPI](../../contracts/openapi.json) 定义路径、认证、conditional headers、响应和错误。上传端点接收 `metadata`（JSON 编码文本）和 `content`（ZIP 文件）两个 multipart 字段；`metadata` 不能作为带 filename 的文件字段发送。

`content_sha256` 是文件 manifest 的摘要，不是 ZIP 文件摘要。以文件路径为 key，每项包含文件字节的 `sha256`、字节数 `size` 和上表 `media_type`；对该对象执行 Python `json.dumps(manifest, sort_keys=True, separators=(",", ":"))` 的默认 ASCII 转义序列化，再对 UTF-8 字节计算 SHA-256。目录成员不进入 manifest。其他语言的实现应产生相同字节；Toolkit 的 `inspect_documentation` 提供可直接复用的实现。

400 表示输入或归档不合法，401/403 表示发布权限错误，404 表示目标不存在或不公开，409 表示 association/内容/地址冲突，411/413/415 表示传输不被接受，412/428 表示条件写入不满足，451 表示 Release 被封禁，503 表示文档托管尚未配置。更换内容指针只发生在所有资源 staging 成功之后；失败时原文档仍有效。
