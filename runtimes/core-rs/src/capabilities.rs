//! 本机业务能力的声明与跨进程数据协议；不包含 Core runtime trait 或数据库实现。

use std::collections::HashSet;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{Error, RpcError};

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Capabilities {
    #[serde(default)]
    pub resolvers: Vec<ResolverCapability>,
    #[serde(default)]
    pub storages: Vec<StorageCapability>,
    #[serde(default)]
    pub sources: Vec<SourceCapability>,
    #[serde(default)]
    pub jobs: Vec<JobCapability>,
}

impl Capabilities {
    pub fn validate(&self) -> Result<(), Error> {
        unique_ids(self.resolvers.iter().map(|item| item.id.as_str()))?;
        unique_ids(self.storages.iter().map(|item| item.id.as_str()))?;
        unique_ids(self.sources.iter().map(|item| item.id.as_str()))?;
        unique_ids(self.jobs.iter().map(|item| item.id.as_str()))?;
        for resolver in &self.resolvers {
            unique_ids(
                resolver
                    .read_methods
                    .iter()
                    .map(|method| method.name.as_str()),
            )?;
            for method in &resolver.read_methods {
                if !(method.name.starts_with("get_") || method.name.starts_with("read_")) {
                    return Err(Error::Protocol(
                        "Resolver 自定义读方法必须以 get_/read_ 开头".into(),
                    ));
                }
                object_schema(&method.input_schema)?;
            }
            if let Some(draft) = &resolver.draft {
                object_schema(&draft.input_schema)?;
            }
            if let Some(schema) = &resolver.content.schema {
                object_schema(schema)?;
            }
            if resolver.content.kind == ContentKind::Json && resolver.content.schema.is_none() {
                return Err(Error::Protocol(
                    "JSON Resolver 必须声明 canonical content schema".into(),
                ));
            }
        }
        for storage in &self.storages {
            object_schema(&storage.config_schema)?;
        }
        for source in &self.sources {
            object_schema(&source.config_schema)?;
            object_schema(&source.collect_config_schema)?;
            if let Some(schema) = &source.backfill_config_schema {
                object_schema(schema)?;
            }
        }
        for job in &self.jobs {
            object_schema(&job.parameters_schema)?;
            if job.default_timeout_seconds <= 0 {
                return Err(Error::Protocol("Job timeout 必须为正数".into()));
            }
        }
        Ok(())
    }
}

fn unique_ids<'a>(ids: impl Iterator<Item = &'a str>) -> Result<(), Error> {
    let mut seen = HashSet::new();
    for id in ids {
        if id.trim().is_empty() || id.len() > 512 || !seen.insert(id) {
            return Err(Error::Protocol("能力 ID 必须非空、有界且唯一".into()));
        }
    }
    Ok(())
}

fn object_schema(schema: &Value) -> Result<(), Error> {
    if !schema.is_object() {
        return Err(Error::Protocol("能力 schema 必须为对象".into()));
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverCapability {
    pub id: String,
    pub description: String,
    pub content: ContentContract,
    #[serde(default)]
    pub relations: RelationSelection,
    #[serde(default)]
    pub read_methods: Vec<ReadMethod>,
    pub draft: Option<DraftCapability>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReadMethod {
    pub name: String,
    pub description: String,
    pub input_schema: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DraftCapability {
    pub description: String,
    pub input_schema: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContentContract {
    pub kind: ContentKind,
    pub schema: Option<Value>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContentKind {
    Text,
    Bytes,
    Json,
}

#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RelationSelection {
    #[serde(default)]
    pub include_in: bool,
    #[serde(default)]
    pub include_out: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StorageCapability {
    pub id: String,
    pub description: String,
    pub config_schema: Value,
    pub writable: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceCapability {
    pub id: String,
    pub description: Option<String>,
    pub config_schema: Value,
    pub collect_config_schema: Value,
    pub backfill_config_schema: Option<Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JobCapability {
    pub id: String,
    pub description: String,
    pub parameters_schema: Value,
    pub default_timeout_seconds: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "kind", content = "content", rename_all = "snake_case")]
pub enum Content {
    Text(String),
    Bytes(Vec<u8>),
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BlockSnapshot {
    pub id: i32,
    pub storage: Option<i32>,
    pub resolver: String,
    pub content: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RelationSnapshot {
    pub id: i32,
    pub from_: Option<i32>,
    pub to_: Option<i32>,
    pub content: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverInput {
    pub block: BlockSnapshot,
    pub content: Content,
    pub relations: Vec<RelationSnapshot>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverRequest {
    pub resolver: String,
    pub input: ResolverInput,
    pub operation: ResolverOperation,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ResolverOperation {
    Solve {
        refresh: bool,
        materialize_missing: bool,
    },
    Text {
        refresh: bool,
        materialize_missing: bool,
        context: TextContext,
    },
    Label {
        refresh: bool,
    },
    Read {
        method: String,
        args: Value,
    },
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TextContext {
    Default,
    Lexical,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverDraftRequest {
    pub resolver: String,
    pub input: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GraphDraft {
    pub root: i32,
    pub blocks: Vec<DraftBlock>,
    pub relations: Vec<DraftRelation>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DraftBlock {
    pub id: i32,
    pub storage: Option<i32>,
    pub resolver: String,
    pub content: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DraftRelation {
    pub from_: i32,
    pub to_: i32,
    pub content: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StorageSnapshot {
    pub id: i32,
    pub type_id: String,
    pub config: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StorageReadRequest {
    pub storage: StorageSnapshot,
    pub pointer: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StorageWriteRequest {
    pub storage: StorageSnapshot,
    pub pointer: Option<String>,
    pub data: Vec<u8>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceRequest {
    pub source: i32,
    pub type_id: String,
    pub job: i64,
    pub config: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JobRequest {
    pub job: i64,
    pub type_id: String,
    pub peer_id: String,
    pub parameters: Value,
    pub state: Value,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JobOutcome {
    /// 写入 Job.state 的对象 patch；Source.state/cursor 由插件自己的事务维护。
    pub state: Value,
}

impl Default for JobOutcome {
    fn default() -> Self {
        Self {
            state: serde_json::json!({}),
        }
    }
}

pub type SourceOutcome = JobOutcome;

pub(crate) fn unsupported() -> RpcError {
    RpcError::new("unsupported_capability", "该业务能力未实现")
}
