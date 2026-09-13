# PR 预览

PR 预览使用 `Dockerfile` 构建的 CPython 服务镜像，覆盖目录、扩展详情、Publisher、Simple API 和文件分发。每个同仓库 PR 拥有 Heroku app `inkcre-ext-reg-pr-<number>`、同名私有 R2 桶，以及 Neon 分支 `preview/ext-reg/pr-<number>`。模板不区分预览和生产，环境只提供运行配置。

新数据库分支来自专用空分支 `preview-base`，运行当前提交的完整迁移历史。基础分支不承载业务数据，不随生产导入而改变；不复制生产数据或凭据。预览分支首次配置时更换继承的 `registry_owner` 密码。更新复用现有分支和桶，保留人工验收数据，仅向前迁移。每次更新将分支到期时间延长七天；到期后数据会丢失，需要长期保留时由运维在 Neon 调整期限。

`registry-preview.yml` 仅接受成功的 `Registry checks`，核验精确 PR head 和同仓库身份。无部署凭据的 build runner 构建镜像，再把镜像交给独立 delivery runner。后者检出可信默认分支控制器，队列后重新确认 PR 仍开放且 head 未改变，再配置资源、迁移和部署。候选镜像只获得所属分支的数据库凭据；运行服务另获对应 R2 桶的对象读写凭据。Heroku、Neon 和 Cloudflare 控制 token 不进入候选容器。

可信控制器使用 Docker / Heroku CLI 交付镜像，使用官方 REST API 配置分支、app 和 R2 凭据。REST 调用只覆盖 CLI 不适合保密结构化配置的部分，数据库业务仍由包内 ORM 命令执行。Neon 分支密码更换与 R2 桶授权分别约束数据库和对象存储的访问范围。

GitHub `preview` 环境需要：

| 配置                                                         | 用途                                               |
| ------------------------------------------------------------ | -------------------------------------------------- |
| `NEON_PROJECT_ID`、`NEON_PREVIEW_PARENT_BRANCH_ID` variables | Registry 专属项目与空基础分支                      |
| `NEON_API_KEY` secret                                        | 仅授权 Registry 项目的分支管理                     |
| `HEROKU_API_KEY` secret                                      | PR app 生命周期及镜像发布                          |
| `CLOUDFLARE_ACCOUNT_ID` variable                             | R2 所在账户                                        |
| `CLOUDFLARE_PREVIEW_API_TOKEN` secret                        | 创建和清理 R2 桶、创建和撤销桶范围的账户 API token |
| `REGISTRY_PREVIEW_PUBLISHER_TOKEN` secret                    | 随机审阅凭据，只登记 `reviewer` namespace          |

Cloudflare 控制 token 的账户级权限只属于可信 runner。应用拿到的 S3 key 来自单个桶的 `Workers R2 Storage Bucket Item Write` token；不要直接把账户管理 token 放入应用。部署只登记审阅者凭据，不生成示例扩展、版本或文件。发布验收应在一次性环境完成，共享预览仅保留明确用于人工审阅的数据。

关闭 PR 由可信 cleanup 工作流核验同仓库与 closed 状态，先停止 app，再清理桶对象、桶和对象 token，删除数据库分支与 app。清理失败保留可定位的资源信息，重新运行同一 PR 的清理命令；不得通过范围搜索删除其他 PR、基础分支或生产资源。

首次采用新控制器时，它必须先进入默认分支，GitHub 环境配置也必须完成。PR 中的代码可通过本机已授权控制器先行验收，但不能把旧 Worker 的成功日志当作 CPython 预览证据。部署产物、真实 URL 和观察结果记录在活动 task packet。
