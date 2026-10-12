# Extension Developer Toolkit

`inkcre-extension-toolkit` is an independent developer/CD distribution. Its
base package owns pure, Registry-compatible native association projections;
the `cli` extra owns HTTP and command dependencies and exposes `inkcre-ext`.
The Registry service may reuse the pure library, but the Toolkit must not
depend on Registry implementation or service runtime state.

The Toolkit prepares Release descriptors, uploads native Module Federation
snapshots, and builds deterministic static preview facades from one explicit,
language-neutral inventory. A facade may contain multiple Extensions and only
the supplied native associations. It rejects Release and path collisions and
reuses the same Registry-owned projection functions for Simple API, wheel,
metadata, Release, manifest, and asset paths.

The Toolkit is not a Registry service or Host SDK. It does not own deployment
installation, Peer enablement, runtime activation, or Extension business
behavior. Package metadata in `toolkit/pyproject.toml`, generated schemas,
source, generated contracts, and build checks are executable authority for its released interface.

发布者可以用 `inkcre-ext prepare-release --request request.json --release-intent intent.json`
消费统一的精确版本交付计划。intent 文件仅包含 `version` 与 `required_native_formats`；
Toolkit 在任何 Registry 写入前核对请求版本和已有声明，并把同一集合传给准备接口。
直接构造 `PrepareReleaseRequest` 的调用者也可以提供声明。声明不进入 wheel 的
`inkcre-extension.json` 执行描述，宿主不需要因此改变安装记录。

intent 由原生项目或发布协调者拥有。Toolkit 不读取第一方其他仓库、猜测上一版本支持，
或维护跨仓库版本表。单格式 intent 合法，所列集合是最小承诺而非允许关联的全集。
`--release-intent` 可省略，以继续对历史已发布版本执行合法补关联；创建新 Release
时仍须在请求中直接给出声明，Registry 会拒绝没有声明的新建请求。
