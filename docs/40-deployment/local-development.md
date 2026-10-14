# 本地开发

Registry 使用 Python 3.13、PDM 和 Node 22 / pnpm。Node 只用于现有设计样式、契约及独立 Web Runtime 包的构建；服务进程只运行 Python。

```bash
pdm install --frozen-lockfile
pnpm install --frozen-lockfile
```

配置 `DATABASE_URL`、`PUBLIC_ORIGIN`、`S3_ENDPOINT_URL`、`S3_BUCKET` 和标准 AWS 凭据 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`。启用插件文档托管时，另设 `DOCUMENTATION_ORIGIN_TEMPLATE`，例如本地的 `http://{snapshot}.docs.localhost`；模板必须把 32 位快照标识放在第一个 DNS label，可带固定前后缀，使每份不可变快照拥有独立 origin。数据库必须是 PostgreSQL；远程连接默认验证 TLS，localhost 可以不启用 TLS。`PUBLIC_ORIGIN` 是 HTTPS origin，本地允许 localhost HTTP，不含路径。文档内容 origin 在生产必须使用 HTTPS；本地只允许 `.localhost`。文件配置是 dotenv 数据，不应当作 shell 脚本执行；应用从进程环境读取配置。

生产内容域可以与管理站使用同一可注册域。这样部署时，作者提供的 HTML/JS 可能接收或干扰父域 Cookie；不得在共享父域设置敏感 Cookie。需要浏览器级站点隔离时，应改用独立可注册域，例如 `registry.example.com` 与 `{snapshot}.exampleusercontent.net`。域名应采用 ASCII/Punycode 配置。

```bash
pnpm db:migrate
pdm run python -m inkcre_extension_registry
```

默认监听 8000，平台通过 `PORT` 指定端口。`/`、`/explore/<namespace>/<name>`、`/publish` 和全部 API 使用同一服务。新库显示真实空态；启动和迁移不会创建示例数据。运维可通过 `pdm run python -m inkcre_extension_registry.admin grant <namespace> --label <label>` 从标准输入登记随机 token，通过 `revoke` 按 namespace 和 label 撤销。不要把 token 写进命令行、日志或仓库。

修改模型后运行 `pnpm db:makemigrations`，审查生成的迁移。Tortoise 1.1 的 `CreateModel` 不会把 `Meta.constraints` 写入数据库，因此新表的 CHECK 约束须使用原生 `AddConstraint` 操作显式添加，参照初始迁移；真实 PostgreSQL 的非法数据验收用于防止约束仅存在于模型描述中。`pnpm db:migrate` 只向前执行；上线后只能追加迁移，修复通过后续迁移完成。交付必须以 `MIGRATION_DATABASE_URL` 指定 owner 连接，服务的 `DATABASE_URL` 使用普通 `registry_app`。本地单账号开发仍可省略迁移变量并复用 `DATABASE_URL`。权限迁移创建 NOLOGIN 角色；生产和预览控制器在迁移后通过 `scripts/registry_database.py` 设置独立密码并启用登录。服务不在请求或启动期间迁移。

完整检查需要空的、一次性的 PostgreSQL 数据库：

```bash
REGISTRY_TEST_DATABASE_URL=postgres://registry:registry-check@localhost:5432/registry_check pnpm check
```

CI 创建 PostgreSQL 17 service；本地使用独立、一次性的 PostgreSQL 实例或 Neon 测试分支。授权迁移会创建实例级角色，因此仅在共享实例内增加一个空数据库不足以隔离这些检查。不得指向共享开发、PR 预览或生产库。验收运行真实迁移，检查模型漂移，通过真实 ORM / PostgreSQL 和本地 Moto S3 服务验证发布、重试、并发冲突、失败回滚、私有分页、文档条件替换与快照域隔离、blocked 读取、GET / HEAD 和 ETag 重验证。迁移使用 owner，业务验收使用 `registry_app`，并验证创建表、修改业务表、写迁移记录和创建角色均被拒绝。D1 导入验收使用临时 SQLite 快照，比较所有逻辑字段的内容摘要。测试仅在空库插入测试记录，并在退出时清理；失败可能保留 schema 和迁移记录，目标库仍须属于一次性验证生命周期。

`pnpm registry:check` 单独执行上述验收，仍需要同一个测试变量。CI 另外拒绝修改或删除已在 base 中存在的迁移，并构建完整服务镜像。测试数据不会写入共享预览。

Registry 通过不可变 Git commit 安装 `InKCre/ui` 的 `@inkcre/ui-web` 公共 Sass 包。修改 `web/registry.scss` 后运行 `pnpm web:build`；生成 CSS 提交到源码，并由 `pnpm web:check` 比对。模板、CSS 和 JavaScript 都随 Python wheel 打包。视觉验收覆盖空态、详情版本选择、Publisher、键盘操作、窄屏和明暗主题。

Toolkit、Core Runtime 与 Web Runtime 保持各自的版本和发布机制。`pnpm build` 构建这些独立产物；Registry 的容器部署不会发布它们，也不会引入单独的前端部署流程。 Web Runtime 的 Core SDK 开发依赖使用官方预构建 GitHub Release tgz，完整性记录在 pnpm 锁文件中；构建无需跨仓检出源码或运行 SDK 准备脚本。

`pnpm packages:check` 在构建后创建独立虚拟环境，通过 wheel metadata 解析安装 Registry 与本次 Toolkit 候选，再执行 `pip check` 和服务 import；它不加载 workspace 源码，防止可编辑安装掩盖错误依赖边界。该检查需要包索引访问并随 `pnpm check` 运行。Registry 的文档 API 要求 Toolkit `>=0.5,<0.6`。Python 改动在所属 project 的 `.changes/` 记录 Towncrier fragment；Web Runtime 使用 `.changeset/`。合并普通改动后，Version PR 才准备版本与 changelog，正式产物只从准备完成的 `main` 发布。

本次独立原生发行与 Peer 参与模型需要先生成候选 SDK 版本才能跨仓验证：Registry 0.3、Toolkit 0.5、Python Runtime 0.2 由既有 `scripts/release.py prepare` 生成，Web Runtime 0.4 由 Changesets 生成，相关 intents 已消费，后续不能再次升版。PR 58 使用维护者授予的 `coordinated-sdk-version-preparation` label 声明同一 PR 内包含功能与机械版本准备。CI 监听 label 添加/移除并从 PR metadata 决定是否传递 `--allow-feature-version-preparation`；日志显示该用途。这个开关只解除行为文件分类限制，仍要求版本/changelog 一致、版本前进、对应 fragments 已消费及全部质量检查。无 label 默认保持原有严格规则。本地完整验收使用 `BASE_REVISION=<base SHA> RELEASE_CHECK_ARGS=--allow-feature-version-preparation pnpm check`。

该候选例外不改变 canonical package 发布触发器、production environment 或 protected-main 权威；Git exact package 与真实 pack 只用于此次有界资格验证。正式包与生产数据库仍按既有发布边界交付。
