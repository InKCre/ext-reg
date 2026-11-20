//! Binary-aware results and hydrated input for the Resolver wire.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{
    BinaryContent, BlockSnapshot, Content, RelationSnapshot, ResolverInput, ResolverOperation,
    ResolverRequest,
};

pub const RESOLVER_VALUE_SERVICE: &str = "resolver.value.v1";
pub const MAX_RESOLVER_FRAME_BYTES: usize = 48 * 1024 * 1024;

/// Explicit wire kind. Arbitrary authored JSON always stays inside `Json`.
#[derive(Debug, Serialize, Deserialize)]
#[serde(
    tag = "kind",
    content = "value",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum ResolverValue {
    Json(Value),
    Bytes(BinaryContent),
    Object(BTreeMap<String, Self>),
    Array(Vec<Self>),
}

impl From<Value> for ResolverValue {
    fn from(value: Value) -> Self {
        Self::Json(value)
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(
    tag = "kind",
    content = "content",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum ResolverContent {
    Text(String),
    Bytes(BinaryContent),
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverValueInput {
    pub block: BlockSnapshot,
    pub content: ResolverContent,
    pub relations: Vec<RelationSnapshot>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolverValueRequest {
    pub resolver: String,
    pub input: ResolverValueInput,
    pub operation: ResolverOperation,
}

impl From<ResolverValueRequest> for ResolverRequest {
    fn from(request: ResolverValueRequest) -> Self {
        let content = match request.input.content {
            ResolverContent::Text(text) => Content::Text(text),
            ResolverContent::Bytes(bytes) => Content::Bytes(bytes.0),
        };
        Self {
            resolver: request.resolver,
            input: ResolverInput {
                block: request.input.block,
                content,
                relations: request.input.relations,
            },
            operation: request.operation,
        }
    }
}
