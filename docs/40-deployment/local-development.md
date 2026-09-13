# 本地开发

Registry 使用 Python 3.13、PDM 和 Node 22 / pnpm。Node 只用于现有设计样式、契约及独立 Web Runtime 包的构建；服务进程只运行 Python。

```bash
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
```

配置 `DATABASE_URL`、`PUBLIC_ORIGIN`、`S3_ENDPOINT_URL`、`S3_BUCKET` 和标准 AWS 凭据 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`。数据库必须是 PostgreSQL；远程连接默认验证 TLS，localhost 可以不启用 TLS。`PUBLIC_ORIGIN` 是 HTTPS origin，本地允许 localhost HTTP，不含路径。文件配置是 dotenv 数据，不应当作 shell 脚本执行；应用从进程环境读取配置。

```bash
pnpm db:migrate
pdm run python -m inkcre_extension_registry
```

默认监听 8000，平台通过 `PORT` 指定端口。`/`、`/explore/<namespace>/<name>`、`/publish` 和全部 API 使用同一服务。新库显示真实空态；启动和迁移不会创建示例数据。运维可通过 `pdm run python -m inkcre_extension_registry.admin grant <namespace> --label <label>` 从标准输入登记随机 token，通过 `revoke` 按 namespace 和 label 撤销。不要把 token 写进命令行、日志或仓库。

修改模型后运行 `pnpm db:makemigrations`，审查生成的迁移。Tortoise 1.1 的 `CreateModel` 不会把 `Meta.constraints` 写入数据库，因此新表的 CHECK 约束须使用原生 `AddConstraint` 操作显式添加，参照初始迁移；真实 PostgreSQL 的非法数据验收用于防止约束仅存在于模型描述中。`pnpm db:migrate` 只向前执行；上线后只能追加迁移，修复通过后续迁移完成。`MIGRATION_DATABASE_URL` 可以单独指定迁移连接，未配置时使用 `DATABASE_URL`。服务不在请求或启动期间迁移。

完整检查需要空的、一次性的 PostgreSQL 数据库：

```bash
REGISTRY_TEST_DATABASE_URL=postgres://registry:registry-check@localhost:5432/registry_check pnpm check
```

CI 创建 PostgreSQL 17 service；本地可以使用一次性数据库或 Neon 测试分支。不得指向共享开发、PR 预览或生产库。验收运行真实迁移，检查模型漂移，通过真实 ORM / PostgreSQL 和本地 Moto S3 服务验证发布、重试、并发冲突、失败回滚、私有分页、blocked 读取及 GET / HEAD。D1 导入验收使用临时 SQLite 快照，比较所有逻辑字段的内容摘要。测试仅在空库插入测试记录，并在退出时清理；失败可能保留 schema 和迁移记录，目标库仍须属于一次性验证生命周期。

`pnpm registry:check` 单独执行上述验收，仍需要同一个测试变量。CI 另外拒绝修改或删除已在 base 中存在的迁移，并构建完整服务镜像。测试数据不会写入共享预览。

Registry 通过不可变 Git commit 安装 `InKCre/ui` 的 `@inkcre/ui-web` 公共 Sass 包。修改 `web/registry.scss` 后运行 `pnpm web:build`；生成 CSS 提交到源码，并由 `pnpm web:check` 比对。模板、CSS 和 JavaScript 都随 Python wheel 打包。视觉验收覆盖空态、详情版本选择、Publisher、键盘操作、窄屏和明暗主题。

Toolkit、Core Runtime 与 Web Runtime 保持各自的版本和发布机制。`pnpm build` 构建这些独立产物；Registry 的容器部署不会发布它们，也不会引入单独的前端部署流程。
