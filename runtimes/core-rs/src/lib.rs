//! 可独立发布的 Rust executable 扩展协议。stdout 只承载有界 JSON-line 消息。
//!
//! SDK 不依赖 Registry 服务或某一 Core 实现；数据库与共享业务事务仍由宿主或
//! 插件显式采用的 Core SDK 拥有。参见同目录 README 的协议和安装约束。

use std::path::{Component, Path};

use async_trait::async_trait;
use semver::{Version, VersionReq};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use tokio::io::{AsyncBufRead, AsyncBufReadExt, AsyncWrite, AsyncWriteExt, BufReader};

mod capabilities;
pub use capabilities::*;

pub const PROTOCOL_VERSION: u32 = 1;
pub const SDK_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const DISTRIBUTION: &str = "rust_stdio";
pub const MAX_FRAME_BYTES: usize = 1024 * 1024;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("扩展 I/O 失败")]
    Io(#[from] std::io::Error),
    #[error("扩展 JSON 无效")]
    Json(#[from] serde_json::Error),
    #[error("扩展协议错误：{0}")]
    Protocol(String),
    #[error("扩展 manifest 无效：{0}")]
    Manifest(String),
}

/// 可信本地安装声明。executable 必须位于 manifest 所在目录内。
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: u32,
    pub name: String,
    pub version: Version,
    pub distribution: String,
    pub host_sdk: String,
    pub host_sdk_version: VersionReq,
    pub protocol_version: u32,
    pub executable: String,
    pub sha256: String,
}

impl Manifest {
    pub fn validate(&self) -> Result<(), Error> {
        validate_name(&self.name)?;
        if self.schema_version != 1 || self.protocol_version != PROTOCOL_VERSION {
            return Err(Error::Manifest("不支持的 schema/protocol version".into()));
        }
        if self.distribution != DISTRIBUTION || self.host_sdk != "core-rs" {
            return Err(Error::Manifest("必须使用 rust_stdio 和 core-rs".into()));
        }
        if !self.version.build.is_empty() {
            return Err(Error::Manifest("版本不接受 SemVer build metadata".into()));
        }
        let sdk =
            Version::parse(SDK_VERSION).map_err(|_| Error::Manifest("SDK 自身版本无效".into()))?;
        if !self.host_sdk_version.matches(&sdk) {
            return Err(Error::Manifest("宿主 SDK 版本不在要求范围内".into()));
        }
        let path = Path::new(&self.executable);
        if self.executable.is_empty()
            || path
                .components()
                .any(|part| !matches!(part, Component::Normal(_)))
            || self.executable.contains('\\')
        {
            return Err(Error::Manifest("executable 必须是目录内相对路径".into()));
        }
        if self.sha256.len() != 64
            || !self
                .sha256
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        {
            return Err(Error::Manifest("sha256 必须是小写十六进制摘要".into()));
        }
        Ok(())
    }
}

pub fn validate_name(name: &str) -> Result<(), Error> {
    let parts: Vec<_> = name.split('/').collect();
    if parts.len() != 2
        || parts.iter().any(|part| {
            part.is_empty()
                || part.len() > 64
                || !part
                    .bytes()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
                || !part.as_bytes()[0].is_ascii_alphanumeric()
                || !part.as_bytes()[part.len() - 1].is_ascii_alphanumeric()
        })
    {
        return Err(Error::Manifest(
            "name 必须是 canonical namespace/name".into(),
        ));
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Descriptor {
    pub name: String,
    pub version: Version,
    pub sdk_version: Version,
    pub protocol_version: u32,
    pub config_schema: Value,
    pub methods: Vec<String>,
    #[serde(default)]
    pub capabilities: Capabilities,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StartContext {
    pub peer_id: String,
    pub config: Value,
    /// 启动时快照；不能用它覆盖其他参与者之后提交的共享 state。
    pub state: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InvokeParams {
    pub method: String,
    pub params: Value,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub protocol_version: u32,
    pub id: u64,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize, thiserror::Error)]
#[error("{code}: {message}")]
#[serde(deny_unknown_fields)]
pub struct RpcError {
    pub code: String,
    pub message: String,
}

impl RpcError {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Response {
    pub protocol_version: u32,
    pub id: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RpcError>,
}

/// 读取一条严格有界帧；不会先无界分配再检查长度。
pub async fn read_frame<R: AsyncBufRead + Unpin>(reader: &mut R) -> Result<Option<Vec<u8>>, Error> {
    let mut frame = Vec::new();
    loop {
        let bytes = reader.fill_buf().await?;
        if bytes.is_empty() {
            return if frame.is_empty() {
                Ok(None)
            } else {
                Err(Error::Protocol("帧缺少换行".into()))
            };
        }
        let newline = bytes.iter().position(|c| *c == b'\n');
        let take = newline.map_or(bytes.len(), |n| n + 1);
        if frame.len() + take > MAX_FRAME_BYTES {
            return Err(Error::Protocol("帧超过大小上限".into()));
        }
        frame.extend_from_slice(&bytes[..take]);
        reader.consume(take);
        if newline.is_some() {
            frame.pop();
            return Ok(Some(frame));
        }
    }
}

pub async fn write_frame<W: AsyncWrite + Unpin, T: Serialize>(
    writer: &mut W,
    value: &T,
) -> Result<(), Error> {
    let mut frame = serde_json::to_vec(value)?;
    if frame.len() + 1 > MAX_FRAME_BYTES {
        return Err(Error::Protocol("帧超过大小上限".into()));
    }
    frame.push(b'\n');
    writer.write_all(&frame).await?;
    writer.flush().await?;
    Ok(())
}

#[async_trait]
pub trait Extension: Send {
    fn descriptor(&self) -> Descriptor;
    async fn start(&mut self, context: StartContext) -> Result<Value, RpcError>;
    async fn invoke(&mut self, method: &str, params: Value) -> Result<Value, RpcError>;
    async fn stop(&mut self) -> Result<(), RpcError>;
    async fn resolver_read(&mut self, _request: ResolverRequest) -> Result<Value, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn resolver_draft(
        &mut self,
        _request: ResolverDraftRequest,
    ) -> Result<GraphDraft, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn storage_read(&mut self, _request: StorageReadRequest) -> Result<Vec<u8>, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn storage_create(&mut self, _request: StorageWriteRequest) -> Result<String, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn storage_update(&mut self, _request: StorageWriteRequest) -> Result<bool, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn storage_delete(&mut self, _request: StorageReadRequest) -> Result<bool, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn source_collect(&mut self, _request: SourceRequest) -> Result<SourceOutcome, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn source_backfill(
        &mut self,
        _request: SourceRequest,
    ) -> Result<SourceOutcome, RpcError> {
        Err(capabilities::unsupported())
    }
    async fn job_can_handle(&mut self, _request: JobRequest) -> Result<bool, RpcError> {
        Ok(true)
    }
    async fn job_execute(&mut self, _request: JobRequest) -> Result<JobOutcome, RpcError> {
        Err(capabilities::unsupported())
    }
}

/// 顺序运行扩展。宿主拥有请求超时与强制回收；SDK 保证状态机和 stdout 协议。
pub async fn serve<E: Extension>(mut extension: E) -> Result<(), Error> {
    let mut input = BufReader::new(tokio::io::stdin());
    let mut output = tokio::io::stdout();
    let mut initialized = false;
    let mut active = false;
    let mut capabilities = Capabilities::default();
    while let Some(frame) = read_frame(&mut input).await? {
        let request: Request = serde_json::from_slice(&frame)?;
        let stopping = request.method == "stop";
        let result = if request.protocol_version != PROTOCOL_VERSION {
            Err(RpcError::new("protocol_version", "不支持的协议版本"))
        } else {
            match request.method.as_str() {
                "initialize" if !initialized => {
                    let descriptor = extension.descriptor();
                    if descriptor.capabilities.validate().is_err() {
                        Err(RpcError::new("descriptor", "业务能力声明无效"))
                    } else {
                        initialized = true;
                        capabilities = descriptor.capabilities.clone();
                        serialize_result(descriptor)
                    }
                }
                "start" if initialized && !active => match serde_json::from_value(request.params) {
                    Ok(context) => match extension.start(context).await {
                        Ok(value) => {
                            active = true;
                            Ok(value)
                        }
                        Err(error) => Err(error),
                    },
                    Err(_) => Err(RpcError::new("invalid_params", "start 参数无效")),
                },
                "invoke" if active => {
                    match serde_json::from_value::<InvokeParams>(request.params) {
                        Ok(params) => extension.invoke(&params.method, params.params).await,
                        Err(_) => Err(RpcError::new("invalid_params", "invoke 参数无效")),
                    }
                }
                "resolver_read" if active => {
                    match serde_json::from_value::<ResolverRequest>(request.params) {
                        Ok(params)
                            if capabilities.resolvers.iter().any(|capability| {
                                capability.id == params.resolver
                                    && match &params.operation {
                                        ResolverOperation::Read { method, .. } => capability
                                            .read_methods
                                            .iter()
                                            .any(|known| known.name == *method),
                                        _ => true,
                                    }
                            }) =>
                        {
                            extension.resolver_read(params).await
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "resolver_read 参数无效")),
                    }
                }
                "resolver_draft" if active => {
                    match serde_json::from_value::<ResolverDraftRequest>(request.params) {
                        Ok(params)
                            if capabilities.resolvers.iter().any(|capability| {
                                capability.id == params.resolver && capability.draft.is_some()
                            }) =>
                        {
                            extension
                                .resolver_draft(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "resolver_draft 参数无效")),
                    }
                }
                "storage_read" if active => {
                    match serde_json::from_value::<StorageReadRequest>(request.params) {
                        Ok(params)
                            if capabilities
                                .storages
                                .iter()
                                .any(|capability| capability.id == params.storage.type_id) =>
                        {
                            extension
                                .storage_read(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "storage_read 参数无效")),
                    }
                }
                "storage_create" if active => {
                    match serde_json::from_value::<StorageWriteRequest>(request.params) {
                        Ok(params)
                            if params.pointer.is_none()
                                && capabilities.storages.iter().any(|capability| {
                                    capability.id == params.storage.type_id && capability.writable
                                }) =>
                        {
                            extension
                                .storage_create(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "storage_create 参数无效")),
                    }
                }
                "storage_update" if active => {
                    match serde_json::from_value::<StorageWriteRequest>(request.params) {
                        Ok(params)
                            if params.pointer.is_some()
                                && capabilities.storages.iter().any(|capability| {
                                    capability.id == params.storage.type_id && capability.writable
                                }) =>
                        {
                            extension
                                .storage_update(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "storage_update 参数无效")),
                    }
                }
                "storage_delete" if active => {
                    match serde_json::from_value::<StorageReadRequest>(request.params) {
                        Ok(params)
                            if capabilities.storages.iter().any(|capability| {
                                capability.id == params.storage.type_id && capability.writable
                            }) =>
                        {
                            extension
                                .storage_delete(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "storage_delete 参数无效")),
                    }
                }
                "source_collect" if active => {
                    match serde_json::from_value::<SourceRequest>(request.params) {
                        Ok(params)
                            if capabilities
                                .sources
                                .iter()
                                .any(|capability| capability.id == params.type_id) =>
                        {
                            extension
                                .source_collect(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "source_collect 参数无效")),
                    }
                }
                "source_backfill" if active => {
                    match serde_json::from_value::<SourceRequest>(request.params) {
                        Ok(params)
                            if capabilities.sources.iter().any(|capability| {
                                capability.id == params.type_id
                                    && capability.backfill_config_schema.is_some()
                            }) =>
                        {
                            extension
                                .source_backfill(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "source_backfill 参数无效")),
                    }
                }
                "job_can_handle" if active => {
                    match serde_json::from_value::<JobRequest>(request.params) {
                        Ok(params)
                            if capabilities
                                .jobs
                                .iter()
                                .any(|capability| capability.id == params.type_id) =>
                        {
                            extension
                                .job_can_handle(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "job_can_handle 参数无效")),
                    }
                }
                "job_execute" if active => {
                    match serde_json::from_value::<JobRequest>(request.params) {
                        Ok(params)
                            if capabilities
                                .jobs
                                .iter()
                                .any(|capability| capability.id == params.type_id) =>
                        {
                            extension
                                .job_execute(params)
                                .await
                                .and_then(serialize_result)
                        }
                        Ok(_) => Err(capabilities::unsupported()),
                        Err(_) => Err(RpcError::new("invalid_params", "job_execute 参数无效")),
                    }
                }
                "stop" => {
                    if active {
                        extension.stop().await.map(|()| json!({"stopped": true}))
                    } else {
                        Ok(json!({"stopped": true}))
                    }
                }
                _ => Err(RpcError::new(
                    "invalid_state",
                    "方法未知或不适用于当前生命周期",
                )),
            }
        };
        let (result, error) = match result {
            Ok(value) => (Some(value), None),
            Err(error) => (None, Some(error)),
        };
        write_frame(
            &mut output,
            &Response {
                protocol_version: PROTOCOL_VERSION,
                id: request.id,
                result,
                error,
            },
        )
        .await?;
        if stopping {
            return Ok(());
        }
    }
    if active {
        let _ = extension.stop().await;
    }
    Ok(())
}

fn serialize_result<T: Serialize>(value: T) -> Result<Value, RpcError> {
    serde_json::to_value(value)
        .map_err(|_| RpcError::new("invalid_result", "业务能力结果不可序列化"))
}
