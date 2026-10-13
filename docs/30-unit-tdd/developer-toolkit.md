# Extension Developer Toolkit

`inkcre-extension-toolkit` is an independent developer/CD distribution. Its
base package owns pure, Registry-compatible native association projections;
the `cli` extra owns HTTP and command dependencies and exposes `inkcre-ext`.
The Registry service may reuse the pure library, but the Toolkit must not
depend on Registry implementation or service runtime state.

Toolkit 0.5 使用 v2 `(name, distribution, version)` 独立发行入口；prepare/publish/yank/unyank 均显式指定 distribution。旧写接口不再被服务接受。

The Toolkit prepares native Release descriptors, uploads native Module Federation
snapshots, and builds deterministic static preview facades from one explicit,
language-neutral inventory. A facade may contain multiple Extensions and only
the supplied native associations. It rejects native-coordinate and path collisions and
reuses the same Registry-owned projection functions for Simple API, wheel,
metadata, native Release, manifest, and asset paths. 静态 facade 只生成 v2 catalog/exact metadata，不伪造新的 v1 统一发行。文档候选保存 distribution，回执校验包含相同 native 坐标。

The Toolkit is not a Registry service or Host SDK. It does not own deployment
installation, Peer enablement, runtime activation, or Extension business
behavior. Package metadata in `toolkit/pyproject.toml`, generated schemas,
source, generated contracts, and build checks are executable authority for its released interface.
