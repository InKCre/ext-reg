# Registry Web

Registry Web is a presentation surface of the CPython service. FastAPI reads the
existing Registry repository and renders autoescaped Jinja templates. Small
browser enhancements cover theme selection, copying an Extension ID, and the
publisher workspace. There is no separately deployed frontend or browser
framework runtime.

## Public discovery

`/` lists published Extensions with server-rendered name search and publisher
filtering. Search is a case-insensitive substring of the canonical name or
nickname; filtering combines with search. An empty Registry and empty search
results have different recovery actions. The page remains useful without JavaScript.

`/explore/{namespace}/{name}` displays published releases and their admitted
native distribution descriptors. Versions are sorted by SemVer; the default
selection is the highest stable version, or the highest pre-release if there
is no stable release. The optional `version` query selects an exact published
version. Missing or withdrawn versions return a human-readable 404. Existing
`/v1`, `/simple`, `/packages`, and Module Federation asset paths retain their
machine-facing semantics.

The UI does not invent descriptions, popularity, trust badges, compatibility
verdicts, installation state, or download counts that Registry does not own.
Package inspection and copying an ID do not install or activate an Extension.

## Publisher workspace

`/publish` connects a namespace credential kept only in the current page's
memory. A reload, navigation away, or disconnect clears it. Credentials are
sent in Authorization headers to the same origin, never in URLs, local storage,
HTML, or logs. Only the theme preference is persisted in local storage.

Connect、复制 ID 和主题按钮在各自的事件处理器绑定后才启用，避免脚本加载期间丢失用户操作。凭据输入框没有原生表单字段名，因此脚本加载延迟或失败时，浏览器不能把凭据作为 URL 查询参数提交；认证仅由脚本通过 Authorization 发出。

`GET /v1/publisher?offset=0` authenticates through the existing namespace
credential dependency and returns only that namespace's releases, including
preparing, withdrawn, and operator-blocked releases. Pages contain at most ten
records. Related distribution and file data is prefetched in bounded queries.
`next_offset` indicates another page; concurrent publication can shift this
non-snapshot listing, and Refresh reloads current state. Private responses,
including rejected credentials, are not cached. Per-distribution uploaded flags
come from the admitted files/manifest association, not a browser assumption.

The Web release form calls the existing prepare endpoint, uploads a Module
Federation ZIP through the existing multipart endpoint, and asks for a separate
publication decision. Failed preparation or upload keeps the form available
for correction; published bytes and metadata remain immutable. The workspace
also withdraws and restores releases through existing lifecycle endpoints.
A failed refresh after a successful mutation is reported separately from a
failed mutation. Timeout messages tell publishers to check state before retrying.

Python releases continue to use the Developer Toolkit/native Python upload
protocol. They appear in the same workspace for publication and lifecycle
management. Namespace and credential issuance remains an operator responsibility.

## Design ownership

`@inkcre/ui-web` is the existing package released by the sibling `design`
repository (`InKCre/ui`). Registry installs the package from its immutable public release commit
using pnpm’s Git subdirectory support, and imports its public Sass styles, token maps,
and functions. This avoids requiring private GitHub Packages access in public CI;
compiled Vue exports are not part of this consumer contract. Colors, typography families, and common spacing/radius vocabulary
remain design-owned; `web/registry.scss` owns Registry page composition. There
is no Registry copy of the token source or a competing design package.

`pnpm web:build` compiles the pinned package and local Sass into the committed
`service/static/registry.css`. `pnpm web:check` compares it to a fresh compilation
and checks browser JavaScript syntax. Committing generated CSS makes Python wheel
and container builds self-contained; it is never edited manually. The wheel
includes templates, CSS and JavaScript in the ordinary Python package.
Rendering depends on product data, selected release, and the current route.
Templates, links, controls, and browser styles contain no preview/production
switch. Instance origin and storage connections belong to runtime configuration.

Remote previews run the same CPython image with an isolated PostgreSQL branch and R2 bucket. Their
resource lifecycle and source identity belong to the delivery controller; see
[Pull-Request Previews](../40-deployment/pull-request-previews.md).

Registry follows the client-web product surface: the 32px geometric InKCre logo,
InkHeader spacing and typography, square InkButton-style controls, bordered
extension rows, and compact metadata. `templates/brand.html` contains the SVG
from client-web's `apps/client-web/public/logo/32.svg`. Page content consists of
catalog, release metadata, and publishing controls; it has no marketing hero,
illustration, promotional footer, or persistent tutorial panels.
