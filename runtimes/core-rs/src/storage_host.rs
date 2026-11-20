//! Storage calls to the current host while it is executing an extension operation.

use std::future::Future;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::{
    io::{AsyncBufRead, AsyncWrite},
    sync::{mpsc, oneshot},
};

use crate::{
    Error, MAX_BINARY_CONTENT_BYTES, PROTOCOL_VERSION, RpcError, StorageSnapshot,
    StorageWriteRequest, read_frame_with_limit, write_frame_with_limit,
};

pub use crate::BinaryContent as StorageBytes;

pub const HOST_STORAGE_SERVICE: &str = "storage.v1";
pub const RESOLVER_STORAGE_MATERIALIZATION_SERVICE: &str = "resolver.storage.materialization.v1";
pub const MAX_STORAGE_CONTENT_BYTES: usize = MAX_BINARY_CONTENT_BYTES;
pub const MAX_STORAGE_FRAME_BYTES: usize = 48 * 1024 * 1024;

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StorageBytesWriteRequest {
    pub storage: StorageSnapshot,
    pub pointer: Option<String>,
    pub data: StorageBytes,
}

impl From<StorageBytesWriteRequest> for StorageWriteRequest {
    fn from(request: StorageBytesWriteRequest) -> Self {
        Self {
            storage: request.storage,
            pointer: request.pointer,
            data: request.data.0,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "action", rename_all = "snake_case", deny_unknown_fields)]
pub enum HostStorageOperation {
    Read {
        storage: i32,
        pointer: String,
    },
    Create {
        storage: i32,
        data: StorageBytes,
    },
    Update {
        storage: i32,
        pointer: String,
        data: StorageBytes,
    },
    Delete {
        storage: i32,
        pointer: String,
    },
}

impl HostStorageOperation {
    fn input_size(&self) -> usize {
        match self {
            Self::Create { data, .. } | Self::Update { data, .. } => data.0.len(),
            _ => 0,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(
    tag = "kind",
    content = "value",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum HostStorageValue {
    Bytes(StorageBytes),
    Pointer(String),
    Exists(bool),
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HostStorageCall {
    pub protocol_version: u32,
    pub host_call: u64,
    pub operation: HostStorageOperation,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HostStorageReply {
    pub protocol_version: u32,
    pub host_reply: u64,
    pub result: Result<HostStorageValue, RpcError>,
}

#[derive(Clone, Copy)]
pub enum HostStorageAccess {
    Read,
    ReadCreate,
    ReadWrite,
}

impl HostStorageAccess {
    pub fn for_method(method: &str) -> Option<Self> {
        match method {
            "resolver_read" | "resolver_read_value" => Some(Self::Read),
            "source_collect" | "source_backfill" | "job_execute" | "invoke" | "http_request" => {
                Some(Self::ReadWrite)
            }
            _ => None,
        }
    }

    /// Compute the same scope in the runner and the Host. The caller must already
    /// have negotiated the service and verified that the current process is active.
    pub fn for_request(method: &str, params: &Value, can_materialize: bool) -> Option<Self> {
        let access = Self::for_method(method)?;
        let operation = &params["operation"];
        if matches!(access, Self::Read)
            && can_materialize
            && matches!(operation["kind"].as_str(), Some("solve" | "text"))
            && operation["materialize_missing"].as_bool() == Some(true)
        {
            return Some(Self::ReadCreate);
        }
        Some(access)
    }

    pub fn allows(self, operation: &HostStorageOperation) -> bool {
        matches!(self, Self::ReadWrite)
            || matches!(operation, HostStorageOperation::Read { .. })
            || (matches!(self, Self::ReadCreate)
                && matches!(operation, HostStorageOperation::Create { .. }))
    }
}

struct Pending {
    operation: HostStorageOperation,
    reply: oneshot::Sender<Result<HostStorageValue, RpcError>>,
}

struct Channel {
    requests: mpsc::Sender<Pending>,
    access: HostStorageAccess,
}

tokio::task_local! {
    static CHANNEL: Channel;
}

/// Borrow a Storage handler from the host for the current extension operation.
/// Returns `None` when called without a negotiated host service.
pub async fn host_storage(
    operation: HostStorageOperation,
) -> Option<Result<HostStorageValue, RpcError>> {
    let (channel, access) = CHANNEL
        .try_with(|channel| (channel.requests.clone(), channel.access))
        .ok()?;
    if !access.allows(&operation) {
        return Some(Err(RpcError::new(
            "storage_read_only",
            "host Storage write is unavailable for this operation",
        )));
    }
    if operation.input_size() > MAX_STORAGE_CONTENT_BYTES {
        return Some(Err(RpcError::new(
            "storage_too_large",
            "host Storage byte input exceeds limit",
        )));
    }
    let unavailable = || RpcError::new("storage_unavailable", "host Storage call is unavailable");
    let (reply, response) = oneshot::channel();
    Some(match channel.send(Pending { operation, reply }).await {
        Ok(()) => response.await.unwrap_or_else(|_| Err(unavailable())),
        Err(_) => Err(unavailable()),
    })
}

pub(crate) async fn scope<F: Future>(
    input: &mut (impl AsyncBufRead + Unpin),
    output: &mut (impl AsyncWrite + Unpin),
    access: Option<HostStorageAccess>,
    execute: F,
) -> Result<F::Output, Error> {
    let Some(access) = access else {
        return Ok(execute.await);
    };
    let (requests, mut pending) = mpsc::channel::<Pending>(1);
    let execute = CHANNEL.scope(Channel { requests, access }, execute);
    tokio::pin!(execute);
    let mut id = 0u64;
    loop {
        let Pending { operation, reply } = tokio::select! {
            biased;
            result = &mut execute => return Ok(result),
            pending = pending.recv() => pending.ok_or_else(|| Error::Protocol("host Storage scope closed".into()))?,
        };
        id = id
            .checked_add(1)
            .ok_or_else(|| Error::Protocol("host Storage request identity exhausted".into()))?;
        let call = HostStorageCall {
            protocol_version: PROTOCOL_VERSION,
            host_call: id,
            operation,
        };
        write_frame_with_limit(output, &call, MAX_STORAGE_FRAME_BYTES).await?;
        let frame = read_frame_with_limit(input, MAX_STORAGE_FRAME_BYTES)
            .await?
            .ok_or_else(|| Error::Protocol("no host Storage response".into()))?;
        let response: HostStorageReply = serde_json::from_slice(&frame)?;
        if response.protocol_version != PROTOCOL_VERSION || response.host_reply != id {
            return Err(Error::Protocol(
                "host Storage response identity mismatch".into(),
            ));
        }
        let _ = reply.send(response.result);
    }
}
